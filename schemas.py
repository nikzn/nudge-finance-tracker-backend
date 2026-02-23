from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime

from common.enum import TransactionTypeEnum





# # Enums
# class TransactionTypeEnum(str, Enum):
#     INCOME = "INCOME"
#     EXPENSE = "EXPENSE"


# Auth Schemas
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    username_or_email: str
    password: str

class UserName(BaseModel):
    name: str

class UsernameCheckResponse(BaseModel):
    exists: bool

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    profile_picture: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenRefresh(BaseModel):
    refresh_token: str




# User Update Schemas
class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


# Category Schemas
class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    transaction_type: TransactionTypeEnum


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None


class CategoryResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    icon: Optional[str]
    color: Optional[str]
    transaction_type: str
    created_at: datetime

    class Config:
        from_attributes = True


# Transaction Type Schemas
class CustomTransactionTypeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class CustomTransactionTypeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None


class CustomTransactionTypeResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# Transaction Schemas
class TransactionCreate(BaseModel):
    amount: float = Field(..., gt=0)
    description: Optional[str] = None
    transaction_type: TransactionTypeEnum
    category_id: Optional[int] = None
    custom_type_id: Optional[int] = None
    transaction_date: Optional[datetime] = None
    notes: Optional[str] = None


class TransactionUpdate(BaseModel):
    amount: Optional[float] = Field(None, gt=0)
    description: Optional[str] = None
    transaction_type: Optional[TransactionTypeEnum] = None
    category_id: Optional[int] = None
    custom_type_id: Optional[int] = None
    transaction_date: Optional[datetime] = None
    notes: Optional[str] = None


class TransactionResponse(BaseModel):
    id: int
    amount: float
    description: Optional[str]
    transaction_type: str
    category_id: Optional[int]
    custom_type_id: Optional[int]
    transaction_date: datetime
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    category: Optional[CategoryResponse]

    class Config:
        from_attributes = True


class TransactionListResponse(BaseModel):
    transactions: List[TransactionResponse]
    total_count: int
    total_income: float
    total_expense: float
    page: int
    page_size: int


# Budget Schemas
class BudgetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    amount: float = Field(..., gt=0)
    category_id: Optional[int] = None
    month: int = Field(..., ge=1, le=12)
    year: int = Field(..., ge=2000, le=2100)
    alert_threshold: Optional[float] = Field(80.0, ge=0, le=100)


class BudgetUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    amount: Optional[float] = Field(None, gt=0)
    category_id: Optional[int] = None
    alert_threshold: Optional[float] = Field(None, ge=0, le=100)


class BudgetResponse(BaseModel):
    id: int
    name: str
    amount: float
    category_id: Optional[int]
    month: int
    year: int
    alert_threshold: float
    spent: float = 0.0
    remaining: float = 0.0
    percentage_used: float = 0.0
    created_at: datetime

    class Config:
        from_attributes = True


# Dashboard Schemas
class DashboardSummary(BaseModel):
    total_income: float
    total_expense: float
    savings: float
    transaction_count: int
    budget_utilization: float


class CategorySpending(BaseModel):
    category_name: str
    amount: float
    percentage: float


class MonthlyData(BaseModel):
    month: str
    income: float
    expense: float


class DashboardResponse(BaseModel):
    summary: DashboardSummary
    category_spending: List[CategorySpending]
    monthly_trend: List[MonthlyData]
    recent_transactions: List[TransactionResponse]


# Report Schemas
class ReportFilter(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    category_id: Optional[int] = None
    transaction_type: Optional[TransactionTypeEnum] = None


class ReportSummary(BaseModel):
    total_income: float
    total_expense: float
    net_savings: float
    transaction_count: int
    category_breakdown: List[CategorySpending]


# User Settings Schemas
class UserSettingsUpdate(BaseModel):
    currency: Optional[str] = None
    date_format: Optional[str] = None
    notification_enabled: Optional[bool] = None
    budget_alerts: Optional[bool] = None
    theme: Optional[str] = None


class UserSettingsResponse(BaseModel):
    id: int
    currency: str
    date_format: str
    notification_enabled: bool
    budget_alerts: bool
    theme: str

    class Config:
        from_attributes = True