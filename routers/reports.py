from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, extract
from typing import Optional
from datetime import datetime
import csv
import io
from collections import defaultdict

from database import get_db
from models import Transaction, User, Category
from schemas import ReportFilter, ReportSummary, CategorySpending
from security import get_current_user
from common.enum import TransactionTypeEnum
router = APIRouter()


@router.post("/summary", response_model=ReportSummary)
async def generate_report_summary(
        filters: ReportFilter,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Generate financial report summary with filters"""
    query = db.query(Transaction).filter(Transaction.user_id == current_user.id)

    # Apply filters
    if filters.start_date:
        query = query.filter(Transaction.transaction_date >= filters.start_date)
    if filters.end_date:
        query = query.filter(Transaction.transaction_date <= filters.end_date)
    if filters.category_id:
        query = query.filter(Transaction.category_id == filters.category_id)
    if filters.transaction_type:
        query = query.filter(Transaction.transaction_type == filters.transaction_type)

    transactions = query.all()

    # Calculate totals
    total_income = sum(t.amount for t in transactions if t.transaction_type == TransactionTypeEnum.INCOME)
    total_expense = sum(t.amount for t in transactions if t.transaction_type == TransactionTypeEnum.EXPENSE)
    net_savings = total_income - total_expense

    # Category breakdown
    category_totals = defaultdict(float)
    for t in transactions:
        if t.category_id and t.transaction_type == TransactionTypeEnum.EXPENSE:
            category_totals[t.category_id] += t.amount

    category_breakdown = []
    for cat_id, amount in category_totals.items():
        category = db.query(Category).filter(Category.id == cat_id).first()
        if category:
            percentage = (amount / total_expense * 100) if total_expense > 0 else 0
            category_breakdown.append(
                CategorySpending(
                    category_name=category.name,
                    amount=amount,
                    percentage=round(percentage, 2)
                )
            )

    category_breakdown.sort(key=lambda x: x.amount, reverse=True)

    return ReportSummary(
        total_income=total_income,
        total_expense=total_expense,
        net_savings=net_savings,
        transaction_count=len(transactions),
        category_breakdown=category_breakdown
    )


@router.get("/monthly")
async def monthly_report(
        month: int = Query(..., ge=1, le=12),
        year: int = Query(..., ge=2000, le=2100),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Generate monthly financial report"""
    # Query transactions for the month
    transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id,
        extract('month', Transaction.transaction_date) == month,
        extract('year', Transaction.transaction_date) == year
    ).all()

    total_income = sum(t.amount for t in transactions if t.transaction_type == TransactionTypeEnum.INCOME)
    total_expense = sum(t.amount for t in transactions if t.transaction_type == TransactionTypeEnum.EXPENSE)

    # Category breakdown
    category_totals = defaultdict(lambda: {"income": 0.0, "expense": 0.0})
    for t in transactions:
        if t.category_id:
            category = db.query(Category).filter(Category.id == t.category_id).first()
            if category:
                if t.transaction_type == TransactionTypeEnum.INCOME:
                    category_totals[category.name]["income"] += t.amount
                else:
                    category_totals[category.name]["expense"] += t.amount

    return {
        "month": month,
        "year": year,
        "total_income": total_income,
        "total_expense": total_expense,
        "net_savings": total_income - total_expense,
        "transaction_count": len(transactions),
        "category_breakdown": dict(category_totals),
        "savings_rate": (total_income - total_expense) / total_income * 100 if total_income > 0 else 0
    }


@router.get("/category-wise")
async def category_wise_report(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Generate category-wise spending report"""
    query = db.query(Transaction).filter(
        Transaction.user_id == current_user.id,
        Transaction.transaction_type == TransactionTypeEnum.EXPENSE
    )

    if start_date:
        query = query.filter(Transaction.transaction_date >= start_date)
    if end_date:
        query = query.filter(Transaction.transaction_date <= end_date)

    transactions = query.all()
    total_expense = sum(t.amount for t in transactions)

    # Group by category
    category_data = defaultdict(lambda: {"total": 0.0, "count": 0, "transactions": []})

    for t in transactions:
        if t.category_id:
            category = db.query(Category).filter(Category.id == t.category_id).first()
            if category:
                cat_name = category.name
                category_data[cat_name]["total"] += t.amount
                category_data[cat_name]["count"] += 1
                category_data[cat_name]["transactions"].append({
                    "id": t.id,
                    "amount": t.amount,
                    "description": t.description,
                    "date": t.transaction_date.isoformat()
                })

    # Calculate percentages
    result = []
    for cat_name, data in category_data.items():
        percentage = (data["total"] / total_expense * 100) if total_expense > 0 else 0
        result.append({
            "category": cat_name,
            "total_spent": data["total"],
            "transaction_count": data["count"],
            "percentage": round(percentage, 2),
            "average_transaction": data["total"] / data["count"] if data["count"] > 0 else 0
        })

    result.sort(key=lambda x: x["total_spent"], reverse=True)

    return {
        "total_expense": total_expense,
        "categories": result
    }


@router.get("/income-vs-expense")
async def income_vs_expense_report(
        months: int = Query(6, ge=1, le=24),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Generate income vs expense comparison report"""
    transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id
    ).order_by(Transaction.transaction_date.desc()).all()

    # Group by month
    monthly_data = defaultdict(lambda: {"income": 0.0, "expense": 0.0})

    for t in transactions:
        month_key = t.transaction_date.strftime("%Y-%m")
        if t.transaction_type == TransactionTypeEnum.INCOME:
            monthly_data[month_key]["income"] += t.amount
        else:
            monthly_data[month_key]["expense"] += t.amount

    # Sort and limit to requested months
    sorted_months = sorted(monthly_data.keys(), reverse=True)[:months]

    result = []
    for month in sorted_months:
        data = monthly_data[month]
        result.append({
            "month": month,
            "income": data["income"],
            "expense": data["expense"],
            "net": data["income"] - data["expense"],
            "savings_rate": (data["income"] - data["expense"]) / data["income"] * 100 if data["income"] > 0 else 0
        })

    return {
        "months": result[::-1],  # Reverse to show oldest first
        "total_income": sum(m["income"] for m in result),
        "total_expense": sum(m["expense"] for m in result),
        "average_monthly_income": sum(m["income"] for m in result) / len(result) if result else 0,
        "average_monthly_expense": sum(m["expense"] for m in result) / len(result) if result else 0
    }


@router.get("/export/csv")
async def export_csv(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Export transactions to CSV"""
    query = db.query(Transaction).filter(Transaction.user_id == current_user.id)

    if start_date:
        query = query.filter(Transaction.transaction_date >= start_date)
    if end_date:
        query = query.filter(Transaction.transaction_date <= end_date)

    transactions = query.order_by(Transaction.transaction_date.desc()).all()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        "ID", "Date", "Type", "Category", "Amount",
        "Description", "Notes"
    ])

    # Write data
    for t in transactions:
        category_name = ""
        if t.category_id:
            category = db.query(Category).filter(Category.id == t.category_id).first()
            if category:
                category_name = category.name

        writer.writerow([
            t.id,
            t.transaction_date.strftime("%Y-%m-%d"),
            t.transaction_type.value,
            category_name,
            t.amount,
            t.description or "",
            t.notes or ""
        ])

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=transactions_{datetime.now().strftime('%Y%m%d')}.csv"
        }
    )