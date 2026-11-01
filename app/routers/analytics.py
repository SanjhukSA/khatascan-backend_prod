"""Analytics endpoints: monthly summary and category breakdown.

Receipts are bucketed by the date printed on the document (receipt_date) and
fall back to the upload date when no date could be read.
"""

import calendar
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from app import schemas
from app.dependencies import get_db
from app.models import Receipt

router = APIRouter(prefix="/analytics", tags=["analytics"])

# The date a receipt counts toward: printed date if we have one, else upload date.
effective_date = func.coalesce(Receipt.receipt_date, func.date(Receipt.created_at))


def _in_month(month: int, year: int):
    return (extract("month", effective_date) == month, extract("year", effective_date) == year)


@router.get("/monthly", response_model=schemas.MonthlySummary)
def monthly_summary(
    month: int = Query(None, ge=1, le=12),
    year: int = Query(None, ge=2020, le=2100),
    db: Session = Depends(get_db),
):
    """
    Spending summary for a month across all receipts (defaults to the current month),
    with a daily breakdown for charting.
    """
    today = date.today()
    month = month or today.month
    year = year or today.year

    total_spent = (
        db.query(func.coalesce(func.sum(Receipt.total), 0.0)).filter(*_in_month(month, year)).scalar()
    )
    receipt_count = db.query(func.count(Receipt.id)).filter(*_in_month(month, year)).scalar()
    avg_per_receipt = round(total_spent / receipt_count, 2) if receipt_count else 0.0

    prev_month, prev_year = (12, year - 1) if month == 1 else (month - 1, year)
    previous_month_total = (
        db.query(func.coalesce(func.sum(Receipt.total), 0.0))
        .filter(*_in_month(prev_month, prev_year))
        .scalar()
    )

    daily_rows = (
        db.query(effective_date.label("day"), func.sum(Receipt.total).label("total"))
        .filter(*_in_month(month, year))
        .group_by(effective_date)
        .order_by(effective_date)
        .all()
    )
    daily_map = {str(row.day): float(row.total) for row in daily_rows}

    days_in_month = calendar.monthrange(year, month)[1]
    daily_breakdown = []
    for day_num in range(1, days_in_month + 1):
        d = date(year, month, day_num)
        if d > today:
            break  # no future days
        daily_breakdown.append(schemas.DailySpend(date=str(d), total=daily_map.get(str(d), 0.0)))

    return schemas.MonthlySummary(
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
    db: Session = Depends(get_db),
):
    """Spending by category for a month: total, share of overall spend, receipt count."""
    today = date.today()
    month = month or today.month
    year = year or today.year

    rows = (
        db.query(
            Receipt.category,
            func.sum(Receipt.total).label("total"),
            func.count(Receipt.id).label("count"),
        )
        .filter(*_in_month(month, year))
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
