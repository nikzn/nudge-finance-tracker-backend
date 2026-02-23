from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, extract
from typing import List, Optional
from datetime import datetime

from database import get_db
from models import Budget, User, Category, Transaction
from schemas import BudgetCreate, BudgetUpdate, BudgetResponse
from security import get_current_user
from common.enum import TransactionTypeEnum
router = APIRouter()


def calculate_budget_spent(budget: Budget, db: Session) -> dict:
    """Calculate spent amount and remaining for a budget"""
    start_date = datetime(budget.year, budget.month, 1)

    # Calculate end date (last day of month)
    if budget.month == 12:
        end_date = datetime(budget.year + 1, 1, 1)
    else:
        end_date = datetime(budget.year, budget.month + 1, 1)

    # Query to get total spent
    query = db.query(func.sum(Transaction.amount)).filter(
        and_(
            Transaction.user_id == budget.user_id,
            Transaction.transaction_type == TransactionTypeEnum.EXPENSE,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date < end_date
        )
    )

    if budget.category_id:
        query = query.filter(Transaction.category_id == budget.category_id)

    spent = query.scalar() or 0.0
    remaining = budget.amount - spent
    percentage = (spent / budget.amount * 100) if budget.amount > 0 else 0

    return {
        "spent": spent,
        "remaining": remaining,
        "percentage_used": round(percentage, 2)
    }


@router.post("/", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
async def create_budget(
        budget_data: BudgetCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Create a new budget"""
    # Validate category if provided
    if budget_data.category_id:
        category = db.query(Category).filter(
            Category.id == budget_data.category_id,
            Category.user_id == current_user.id
        ).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )

    # Check for duplicate budget
    existing = db.query(Budget).filter(
        Budget.user_id == current_user.id,
        Budget.category_id == budget_data.category_id,
        Budget.month == budget_data.month,
        Budget.year == budget_data.year
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Budget already exists for this category and period"
        )

    budget = Budget(
        name=budget_data.name,
        amount=budget_data.amount,
        category_id=budget_data.category_id,
        user_id=current_user.id,
        month=budget_data.month,
        year=budget_data.year,
        alert_threshold=budget_data.alert_threshold
    )

    db.add(budget)
    db.commit()
    db.refresh(budget)

    # Calculate spent amount
    budget_info = calculate_budget_spent(budget, db)
    response = BudgetResponse.from_orm(budget)
    response.spent = budget_info["spent"]
    response.remaining = budget_info["remaining"]
    response.percentage_used = budget_info["percentage_used"]

    return response


@router.get("/", response_model=List[BudgetResponse])
async def list_budgets(
        month: Optional[int] = Query(None, ge=1, le=12),
        year: Optional[int] = Query(None, ge=2000, le=2100),
        category_id: Optional[int] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """List all budgets with optional filters"""
    query = db.query(Budget).filter(Budget.user_id == current_user.id)

    if month:
        query = query.filter(Budget.month == month)
    if year:
        query = query.filter(Budget.year == year)
    if category_id:
        query = query.filter(Budget.category_id == category_id)

    budgets = query.order_by(Budget.year.desc(), Budget.month.desc()).all()

    # Calculate spent for each budget
    response = []
    for budget in budgets:
        budget_info = calculate_budget_spent(budget, db)
        budget_response = BudgetResponse.from_orm(budget)
        budget_response.spent = budget_info["spent"]
        budget_response.remaining = budget_info["remaining"]
        budget_response.percentage_used = budget_info["percentage_used"]
        response.append(budget_response)

    return response


@router.get("/{budget_id}", response_model=BudgetResponse)
async def get_budget(
        budget_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get a specific budget"""
    budget = db.query(Budget).filter(
        Budget.id == budget_id,
        Budget.user_id == current_user.id
    ).first()

    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found"
        )

    budget_info = calculate_budget_spent(budget, db)
    response = BudgetResponse.from_orm(budget)
    response.spent = budget_info["spent"]
    response.remaining = budget_info["remaining"]
    response.percentage_used = budget_info["percentage_used"]

    return response


@router.put("/{budget_id}", response_model=BudgetResponse)
async def update_budget(
        budget_id: int,
        budget_data: BudgetUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Update a budget"""
    budget = db.query(Budget).filter(
        Budget.id == budget_id,
        Budget.user_id == current_user.id
    ).first()

    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found"
        )

    # Update fields
    if budget_data.name is not None:
        budget.name = budget_data.name
    if budget_data.amount is not None:
        budget.amount = budget_data.amount
    if budget_data.category_id is not None:
        budget.category_id = budget_data.category_id
    if budget_data.alert_threshold is not None:
        budget.alert_threshold = budget_data.alert_threshold

    db.commit()
    db.refresh(budget)

    budget_info = calculate_budget_spent(budget, db)
    response = BudgetResponse.from_orm(budget)
    response.spent = budget_info["spent"]
    response.remaining = budget_info["remaining"]
    response.percentage_used = budget_info["percentage_used"]

    return response


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
        budget_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Delete a budget"""
    budget = db.query(Budget).filter(
        Budget.id == budget_id,
        Budget.user_id == current_user.id
    ).first()

    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found"
        )

    db.delete(budget)
    db.commit()
    return None


@router.get("/monthly/overview")
async def get_monthly_budget_overview(
        month: int = Query(..., ge=1, le=12),
        year: int = Query(..., ge=2000, le=2100),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get monthly budget overview with all budgets and spending"""
    budgets = db.query(Budget).filter(
        Budget.user_id == current_user.id,
        Budget.month == month,
        Budget.year == year
    ).all()

    total_budgeted = sum(b.amount for b in budgets)
    total_spent = 0.0
    budget_details = []

    for budget in budgets:
        budget_info = calculate_budget_spent(budget, db)
        total_spent += budget_info["spent"]

        budget_details.append({
            "budget_id": budget.id,
            "name": budget.name,
            "category_id": budget.category_id,
            "budgeted": budget.amount,
            "spent": budget_info["spent"],
            "remaining": budget_info["remaining"],
            "percentage_used": budget_info["percentage_used"],
            "alert_threshold": budget.alert_threshold,
            "is_over_budget": budget_info["spent"] > budget.amount,
            "is_near_limit": budget_info["percentage_used"] >= budget.alert_threshold
        })

    return {
        "month": month,
        "year": year,
        "total_budgeted": total_budgeted,
        "total_spent": total_spent,
        "total_remaining": total_budgeted - total_spent,
        "overall_percentage": (total_spent / total_budgeted * 100) if total_budgeted > 0 else 0,
        "budgets": budget_details
    }