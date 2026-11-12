"""Analytics endpoints: monthly summary and category breakdown.

Receipts are bucketed by the date printed on the document (receipt_date) and
fall back to the upload date (in settings.app_timezone) when no date could be read.
Amounts are only summed within one currency (default INR), never mixed.
"""

import calendar
from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from app import schemas
from app.config import settings
from app.database import engine
from app.dependencies import get_current_user, get_db
from app.models import Receipt, User

router = APIRouter(prefix="/analytics", tags=["analytics"])

# The date a receipt counts toward: printed date if we have one, else upload date
# in the app's timezone (a 01:30 IST upload on the 1st must not land in last month).
if engine.dialect.name == "postgresql":
    _upload_day = func.date(func.timezone(settings.app_timezone, Receipt.created_at))
else:
    _upload_day = func.date(Receipt.created_at)
effective_date = func.coalesce(Receipt.receipt_date, _upload_day)


def _today() -> date:
    return datetime.now(ZoneInfo(settings.app_timezone)).date()


def _in_month(month: int, year: int, currency: str, user_id):
    return (
        extract("month", effective_date) == month,
        extract("year", effective_date) == year,
        Receipt.currency == currency,
        Receipt.user_id == user_id,
    )


@router.get("/monthly", response_model=schemas.MonthlySummary)
def monthly_summary(
    month: int = Query(None, ge=1, le=12),
    year: int = Query(None, ge=2020, le=2100),
    currency: str = Query("INR", min_length=3, max_length=3, description="Only receipts in this currency are summed."),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Spending summary for a month (defaults to the current month) in one currency,
    with a daily breakdown for charting.
    """
    today = _today()
    month = month or today.month
    year = year or today.year
    currency = currency.upper()

    total_spent = (
        db.query(func.coalesce(func.sum(Receipt.total), 0.0)).filter(*_in_month(month, year, currency, user.id)).scalar()
    )
    receipt_count = db.query(func.count(Receipt.id)).filter(*_in_month(month, year, currency, user.id)).scalar()
    avg_per_receipt = round(total_spent / receipt_count, 2) if receipt_count else 0.0

    prev_month, prev_year = (12, year - 1) if month == 1 else (month - 1, year)
    previous_month_total = (
        db.query(func.coalesce(func.sum(Receipt.total), 0.0))
        .filter(*_in_month(prev_month, prev_year, currency, user.id))
        .scalar()
    )

    daily_rows = (
        db.query(effective_date.label("day"), func.sum(Receipt.total).label("total"))
        .filter(*_in_month(month, year, currency, user.id))
        .group_by(effective_date)
        .order_by(effective_date)
        .all()
    )
    daily_map = {str(row.day): float(row.total) for row in daily_rows}

    # No empty future days, but a receipt dated tomorrow (allowed by the date parser)
    # still gets its bar so the bars always add up to total_spent.
    last_day = max([today] + [date.fromisoformat(k) for k in daily_map])
    days_in_month = calendar.monthrange(year, month)[1]
    daily_breakdown = []
    for day_num in range(1, days_in_month + 1):
        d = date(year, month, day_num)
        if d > last_day:
            break
        daily_breakdown.append(schemas.DailySpend(date=str(d), total=daily_map.get(str(d), 0.0)))

    return schemas.MonthlySummary(
        currency=currency,
        month=month,
        year=year,
        total_spent=round(float(total_spent), 2),
        receipt_count=receipt_count,
        avg_per_receipt=avg_per_receipt,
        previous_month_total=round(float(previous_month_total), 2),
        daily_breakdown=daily_breakdown,
    )


@router.get("/categories", response_model=list[schemas.CategoryBreakdownItem])
def category_breakdown(
    month: int = Query(None, ge=1, le=12),
    year: int = Query(None, ge=2020, le=2100),
    currency: str = Query("INR", min_length=3, max_length=3),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Spending by category for a month in one currency: total, share of spend, receipt count."""
    today = _today()
    month = month or today.month
    year = year or today.year
    currency = currency.upper()

    rows = (
        db.query(
            Receipt.category,
            func.sum(Receipt.total).label("total"),
            func.count(Receipt.id).label("count"),
        )
        .filter(*_in_month(month, year, currency, user.id))
        .group_by(Receipt.category)
        .order_by(func.sum(Receipt.total).desc())
        .all()
    )

    grand_total = sum(float(r.total) for r in rows) or 1.0  # avoid division by zero

    return [
        schemas.CategoryBreakdownItem(
            category=row.category or "Other",
            total=round(float(row.total), 2),
            percentage=round(float(row.total) / grand_total * 100, 1),
            count=row.count,
        )
        for row in rows
    ]