from .database import SessionLocal
from .main import today
from .seed import seed

if __name__ == "__main__":
    with SessionLocal() as session:
        seed(session, today())
    print("Islamabad directory synced; demo workflows checked and existing workflow data preserved.")
