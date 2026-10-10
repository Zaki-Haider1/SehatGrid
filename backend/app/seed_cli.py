from .database import SessionLocal
from .main import today
from .seed import seed

if __name__ == "__main__":
    with SessionLocal() as session:
        seed(session, today())
    print("Synthetic seed checked; existing data preserved.")
