
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_
from datetime import datetime, timedelta
from collections import defaultdict

from database import get_db
from models import Transaction, User, Category, Budget
from schemas import (
    DashboardResponse, DashboardSummary, CategorySpending,
    MonthlyData, TransactionResponse,
)

from common.enum import TransactionTypeEnum

from security import get_current_user

router = APIRouter()


@router.get("/", response_model=DashboardResponse)
async def get_dashboard(
        months: int = Query(6, ge=1, le=12),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get comprehensive dashboard data"""
    # Get all transactions
    transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id
    ).order_by(Transaction.transaction_date.desc()).all()

    # Calculate totals
    total_income = sum(t.amount for t in transactions if t.transaction_type == TransactionTypeEnum.INCOME)
    total_expense = sum(t.amount for t in transactions if t.transaction_type == TransactionTypeEnum.EXPENSE)
    savings = total_income - total_expense

    # Get current month budgets
    current_month = datetime.now().month
    current_year = datetime.now().year

    budgets = db.query(Budget).filter(
        Budget.user_id == current_user.id,
        Budget.month == current_month,
        Budget.year == current_year
    ).all()

    total_budgeted = sum(b.amount for b in budgets)

    # Calculate monthly expenses for current month
    monthly_expenses = db.query(func.sum(Transaction.amount)).filter(
        and_(
            Transaction.user_id == current_user.id,
            Transaction.transaction_type == TransactionTypeEnum.EXPENSE,
            extract('month', Transaction.transaction_date) == current_month,
            extract('year', Transaction.transaction_date) == current_year
        )
    ).scalar() or 0.0

    budget_utilization = (monthly_expenses / total_budgeted * 100) if total_budgeted > 0 else 0

    # Summary
    summary = DashboardSummary(
        total_income=total_income,
        total_expense=total_expense,
        savings=savings,
        transaction_count=len(transactions),
        budget_utilization=round(budget_utilization, 2)
    )

    # Category spending (top 5)
    category_totals = defaultdict(float)
    for t in transactions:
        if t.category_id and t.transaction_type == TransactionTypeEnum.EXPENSE:
            category_totals[t.category_id] += t.amount

    category_spending = []
    for cat_id, amount in sorted(category_totals.items(), key=lambda x: x[1], reverse=True)[:5]:
        category = db.query(Category).filter(Category.id == cat_id).first()
        if category:
            percentage = (amount / total_expense * 100) if total_expense > 0 else 0
            category_spending.append(
                CategorySpending(
                    category_name=category.name,
                    amount=amount,
                    percentage=round(percentage, 2)
                )
            )

    # Monthly trend
    monthly_data = defaultdict(lambda: {"income": 0.0, "expense": 0.0})

    for t in transactions:
        month_key = t.transaction_date.strftime("%Y-%m")
        print(
            month_key,
            t.amount,
            t.transaction_type,
            t.transaction_type == TransactionTypeEnum.INCOME,
            t.transaction_type == TransactionTypeEnum.EXPENSE
        )

        if t.transaction_type.value == TransactionTypeEnum.INCOME.value:
            monthly_data[month_key]["income"] += t.amount
        elif t.transaction_type.value == TransactionTypeEnum.EXPENSE.value:
            monthly_data[month_key]["expense"] += t.amount

    sorted_months = sorted(monthly_data.keys(), reverse=True)[:months]
    monthly_trend = []
    for month in sorted_months[::-1]:  # Oldest first
        data = monthly_data[month]

        monthly_trend.append(
            MonthlyData(
                month=month,
                income=data["income"],
                expense=data["expense"]
            )
        )


    # Recent transactions (last 10)
    recent_transactions = transactions[:10]

    return DashboardResponse(
        summary=summary,
        category_spending=category_spending,
        monthly_trend=monthly_trend,
        recent_transactions=recent_transactions
    )


@router.get("/summary")
async def get_summary(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get quick summary statistics"""
    # All time totals
    all_transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id
    ).all()

    total_income = sum(t.amount for t in all_transactions if t.transaction_type == TransactionTypeEnum.INCOME)
    total_expense = sum(t.amount for t in all_transactions if t.transaction_type == TransactionTypeEnum.EXPENSE)

    # Current month
    current_month = datetime.now().month
    current_year = datetime.now().year

    month_transactions = [
        t for t in all_transactions
        if t.transaction_date.month == current_month and t.transaction_date.year == current_year
    ]

    month_income = sum(t.amount for t in month_transactions if t.transaction_type == TransactionTypeEnum.INCOME)
    month_expense = sum(t.amount for t in month_transactions if t.transaction_type == TransactionTypeEnum.EXPENSE)

    # Last month
    last_month = current_month - 1 if current_month > 1 else 12
    last_year = current_year if current_month > 1 else current_year - 1

    last_month_transactions = [
        t for t in all_transactions
        if t.transaction_date.month == last_month and t.transaction_date.year == last_year
    ]

    last_month_expense = sum(
        t.amount for t in last_month_transactions if t.transaction_type == TransactionTypeEnum.EXPENSE)

    # Calculate trends
    expense_trend = ((month_expense - last_month_expense) / last_month_expense * 100) if last_month_expense > 0 else 0

    return {
        "all_time": {
            "total_income": total_income,
            "total_expense": total_expense,
            "net_savings": total_income - total_expense,
            "transaction_count": len(all_transactions)
        },
        "current_month": {
            "income": month_income,
            "expense": month_expense,
            "savings": month_income - month_expense,
            "transaction_count": len(month_transactions)
        },
        "trends": {
            "expense_change_percentage": round(expense_trend, 2),
            "expense_direction": "up" if expense_trend > 0 else "down" if expense_trend < 0 else "stable"
        }
    }


@router.get("/charts/category-distribution")
async def category_distribution(
        months: int = Query(1, ge=1, le=12),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get data for category distribution pie chart"""
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30 * months)

    transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id,
        Transaction.transaction_type == TransactionTypeEnum.EXPENSE,
        Transaction.transaction_date >= start_date
    ).all()

    total = sum(t.amount for t in transactions)

    category_data = defaultdict(float)
    for t in transactions:
        if t.category_id:
            category = db.query(Category).filter(Category.id == t.category_id).first()
            if category:
                category_data[category.name] += t.amount
        else:
            category_data["Uncategorized"] += t.amount

    result = [
        {
            "category": name,
            "amount": amount,
            "percentage": round(amount / total * 100, 2) if total > 0 else 0
        }
        for name, amount in sorted(category_data.items(), key=lambda x: x[1], reverse=True)
    ]

    return {
        "total": total,
        "data": result
    }


@router.get("/charts/monthly-trend")
async def monthly_trend(
        months: int = Query(6, ge=1, le=12),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get data for monthly income/expense trend chart"""
    transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id
    ).all()

    monthly_data = defaultdict(lambda: {"income": 0.0, "expense": 0.0})

    for t in transactions:
        month_key = t.transaction_date.strftime("%Y-%m")
        if t.transaction_type == TransactionTypeEnum.INCOME:
            monthly_data[month_key]["income"] += t.amount
        else:
            monthly_data[month_key]["expense"] += t.amount

    sorted_months = sorted(monthly_data.keys(), reverse=True)[:months]

    result = [
        {
            "month": month,
            "income": monthly_data[month]["income"],
            "expense": monthly_data[month]["expense"],
            "net": monthly_data[month]["income"] - monthly_data[month]["expense"]
        }
        for month in sorted_months[::-1]
    ]

    return {"data": result}