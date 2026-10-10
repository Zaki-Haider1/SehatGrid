from app.mvp.seed import seed
from app.database import SessionLocal

if __name__ == "__main__":
    with SessionLocal() as session:
        seed(session)
