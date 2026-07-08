import asyncio
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)

sys.path.append(BACKEND_DIR)
from database.connection import get_db
from models.travel import Company, ServiceType


companies = [
    Company(
        company_id="adani-001",
        name="Adani Group",
        allowed_services=[
            ServiceType.FLIGHT,
            ServiceType.HOTEL,
        ],
    ),

    Company(
        company_id="iocl-001",
        name="Indian Oil Corporation",
        allowed_services=[
            ServiceType.FLIGHT,
        ],
    ),

    Company(
        company_id="reliance-001",
        name="Reliance Industries",
        allowed_services=list(ServiceType),
    ),

    Company(
        company_id="tcs-001",
        name="TCS",
        allowed_services=[
            ServiceType.FLIGHT,
            ServiceType.HOTEL,
            ServiceType.CAR,
        ],
    ),

    Company(
        company_id="infosys-001",
        name="Infosys",
        allowed_services=list(ServiceType),
    ),

    Company(
        company_id="guest-000",
        name="Guest",
        allowed_services=list(ServiceType),
    ),
]


async def seed():

    db = get_db()

    for company in companies:

        await db.companies.update_one(
            {
                "company_id": company.company_id
            },
            {
                "$set": company.dict()
            },
            upsert=True,
        )

        print(f"Inserted {company.name}")

    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(seed())