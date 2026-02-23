from fastapi import HTTPException,status,Depends
from models import UserModel
from sqlalchemy.orm import Session
from schemas import UserCreate
from security import hash_password, verify_password

#create user
def create_user(db: Session, user: UserCreate):
    hashed_pw = hash_password(user.password)
    db_user = UserModel(email=user.email, password=hashed_pw, name=user.name)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# def create_user(db:Session, data:UserCreate) :
#     hashed_password = get_password_hash(data.password)
#     user_instance = User(**data.model_dump())
#     db.add(user_instance)
#     db.commit()
#     db.refresh(user_instance)
#     return user_instance

def get_user(db:Session):
    return db.query(UserModel).all()

def get_username(db: Session, user_name: str):
    user = db.query(UserModel).filter(UserModel.name == user_name).first()
    return {"exists": bool(user)}


def authenticate_user(db: Session, email: str, password: str):
    user = db.query(UserModel).filter(UserModel.email == email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    if not verify_password(password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    return {"data": user, "message": "Login successful"}

