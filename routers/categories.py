from fastapi import APIRouter, Depends, HTTPException, status,Request
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from models import Category, User
from schemas import CategoryCreate, CategoryUpdate, CategoryResponse
from security import get_current_user
from common.enum import TransactionTypeEnum
router = APIRouter()


@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    request: Request,
    category_data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    existing = db.query(Category).filter(
        Category.name == category_data.name,
        Category.user_id == current_user.id,
        Category.transaction_type == category_data.transaction_type.value
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this name already exists for this transaction type"
        )

    category = Category(
        name=category_data.name,
        description=category_data.description,
        icon=category_data.icon,
        color=category_data.color,
        transaction_type=category_data.transaction_type.value,
        user_id=current_user.id
    )

    db.add(category)
    db.commit()
    db.refresh(category)
    return category



@router.get("/", response_model=List[CategoryResponse])
async def list_categories(
        transaction_type: Optional[TransactionTypeEnum] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """List all categories for the current user"""
    query = db.query(Category).filter(Category.user_id == current_user.id)

    if transaction_type:
        query = query.filter(Category.transaction_type == transaction_type)

    categories = query.order_by(Category.name).all()
    return categories


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
        category_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get a specific category"""
    category = db.query(Category).filter(
        Category.id == category_id,
        Category.user_id == current_user.id
    ).first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    return category


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
        category_id: int,
        category_data: CategoryUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Update a category"""
    category = db.query(Category).filter(
        Category.id == category_id,
        Category.user_id == current_user.id
    ).first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    # Check for duplicate name if name is being changed
    if category_data.name and category_data.name != category.name:
        existing = db.query(Category).filter(
            Category.name == category_data.name,
            Category.user_id == current_user.id,
            Category.transaction_type == category.transaction_type,
            Category.id != category_id
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category with this name already exists"
            )

    # Update fields
    if category_data.name is not None:
        category.name = category_data.name
    if category_data.description is not None:
        category.description = category_data.description
    if category_data.icon is not None:
        category.icon = category_data.icon
    if category_data.color is not None:
        category.color = category_data.color

    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
        category_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Delete a category"""
    category = db.query(Category).filter(
        Category.id == category_id,
        Category.user_id == current_user.id
    ).first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    # Check if category has transactions
    if category.transactions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete category with existing transactions"
        )

    db.delete(category)
    db.commit()
    return None