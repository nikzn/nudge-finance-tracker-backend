from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import Optional, List
from datetime import datetime

from database import get_db
from models import Transaction, User, Category, CustomTransactionType
from schemas import (
    TransactionCreate, TransactionUpdate, TransactionResponse,
    TransactionListResponse, CustomTransactionTypeCreate,
    CustomTransactionTypeUpdate, CustomTransactionTypeResponse,

)
from security import get_current_user
from common.enum import TransactionTypeEnum
router = APIRouter()


# Transaction CRUD Operations
@router.post("/", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
        transaction_data: TransactionCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Create a new transaction"""
    # Validate category if provided
    if transaction_data.category_id:
        category = db.query(Category).filter(
            Category.id == transaction_data.category_id,
            Category.user_id == current_user.id
        ).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )

    # Validate custom type if provided
    if transaction_data.custom_type_id:
        custom_type = db.query(CustomTransactionType).filter(
            CustomTransactionType.id == transaction_data.custom_type_id
        ).first()
        if not custom_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Custom transaction type not found"
            )

    # Create transaction
    transaction = Transaction(
        user_id=current_user.id,
        amount=transaction_data.amount,
        description=transaction_data.description,
        transaction_type=transaction_data.transaction_type,
        category_id=transaction_data.category_id,
        custom_type_id=transaction_data.custom_type_id,
        transaction_date=transaction_data.transaction_date or datetime.utcnow(),
        notes=transaction_data.notes
    )

    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


@router.get("/", response_model=TransactionListResponse)
async def list_transactions(
        transaction_type: Optional[TransactionTypeEnum] = None,
        category_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = Query(1, ge=1),
        page_size: int = Query(50, ge=1, le=100),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """List transactions with filters"""
    query = db.query(Transaction).filter(Transaction.user_id == current_user.id)

    # Apply filters
    if transaction_type:
        query = query.filter(Transaction.transaction_type == transaction_type)
    if category_id:
        query = query.filter(Transaction.category_id == category_id)
    if start_date:
        query = query.filter(Transaction.transaction_date >= start_date)
    if end_date:
        query = query.filter(Transaction.transaction_date <= end_date)

    # Get totals
    total_count = query.count()

    income_sum = db.query(func.sum(Transaction.amount)).filter(
        and_(
            Transaction.user_id == current_user.id,
            Transaction.transaction_type == TransactionTypeEnum.INCOME
        )
    ).scalar() or 0.0

    expense_sum = db.query(func.sum(Transaction.amount)).filter(
        and_(
            Transaction.user_id == current_user.id,
            Transaction.transaction_type == TransactionTypeEnum.EXPENSE
        )
    ).scalar() or 0.0

    # Apply pagination
    transactions = query.order_by(
        Transaction.transaction_date.desc()
    ).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "transactions": transactions,
        "total_count": total_count,
        "total_income": income_sum,
        "total_expense": expense_sum,
        "page": page,
        "page_size": page_size
    }


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
        transaction_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get a specific transaction"""
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == current_user.id
    ).first()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )

    return transaction


@router.put("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
        transaction_id: int,
        transaction_data: TransactionUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Update a transaction"""
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == current_user.id
    ).first()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )

    # Update fields
    if transaction_data.amount is not None:
        transaction.amount = transaction_data.amount
    if transaction_data.description is not None:
        transaction.description = transaction_data.description
    if transaction_data.transaction_type is not None:
        transaction.transaction_type = transaction_data.transaction_type
    if transaction_data.category_id is not None:
        transaction.category_id = transaction_data.category_id
    if transaction_data.custom_type_id is not None:
        transaction.custom_type_id = transaction_data.custom_type_id
    if transaction_data.transaction_date is not None:
        transaction.transaction_date = transaction_data.transaction_date
    if transaction_data.notes is not None:
        transaction.notes = transaction_data.notes

    db.commit()
    db.refresh(transaction)
    return transaction


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
        transaction_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Delete a transaction"""
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == current_user.id
    ).first()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )

    db.delete(transaction)
    db.commit()
    return None


# Custom Transaction Types
@router.post("/types/", response_model=CustomTransactionTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_custom_type(
        type_data: CustomTransactionTypeCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Create a custom transaction type"""
    custom_type = CustomTransactionType(
        name=type_data.name,
        description=type_data.description,
        user_id=current_user.id
    )

    db.add(custom_type)
    db.commit()
    db.refresh(custom_type)
    return custom_type


@router.get("/types/", response_model=List[CustomTransactionTypeResponse])
async def list_custom_types(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """List all custom transaction types"""
    types = db.query(CustomTransactionType).filter(
        CustomTransactionType.user_id == current_user.id
    ).all()
    return types


@router.put("/types/{type_id}", response_model=CustomTransactionTypeResponse)
async def update_custom_type(
        type_id: int,
        type_data: CustomTransactionTypeUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Update a custom transaction type"""
    custom_type = db.query(CustomTransactionType).filter(
        CustomTransactionType.id == type_id,
        CustomTransactionType.user_id == current_user.id
    ).first()

    if not custom_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom transaction type not found"
        )

    if type_data.name is not None:
        custom_type.name = type_data.name
    if type_data.description is not None:
        custom_type.description = type_data.description

    db.commit()
    db.refresh(custom_type)
    return custom_type


@router.delete("/types/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_custom_type(
        type_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Delete a custom transaction type"""
    custom_type = db.query(CustomTransactionType).filter(
        CustomTransactionType.id == type_id,
        CustomTransactionType.user_id == current_user.id
    ).first()

    if not custom_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom transaction type not found"
        )

    db.delete(custom_type)
    db.commit()
    return None