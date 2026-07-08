"""
Permission Service.
Checks whether a company's subscription includes the requested service type.
Feature 7: Company Based Service Restriction.
"""

import logging
from typing import Optional, List, Tuple

from database.connection import get_db
from models.travel import ServiceType, Company

logger = logging.getLogger(__name__)

# Default companies seeded for demo — real ones are in MongoDB
DEFAULT_COMPANIES = {
    "ADANI": Company(
        company_id="adani-001",
        name="Adani Group",
        allowed_services=[ServiceType.FLIGHT, ServiceType.HOTEL],
    ),
    "RELIANCE": Company(
        company_id="reliance-001",
        name="Reliance Industries",
        allowed_services=list(ServiceType),
    ),
    "TCS": Company(
        company_id="tcs-001",
        name="TCS",
        allowed_services=[ServiceType.FLIGHT, ServiceType.HOTEL, ServiceType.CAR],
    ),
    "INFOSYS": Company(
        company_id="infosys-001",
        name="Infosys",
        allowed_services=list(ServiceType),
    ),
    "GUEST": Company(
        company_id="guest-000",
        name="Guest / Personal",
        allowed_services=list(ServiceType),
    ),
}


class PermissionService:

    async def get_company(self, company_id: str) -> Optional[Company]:
        """
        Load company from MongoDB.
        Returns None if company does not exist.
        """

        try:

            db = get_db()

            doc = await db.companies.find_one(
                {
                    "company_id": company_id
                }
            )

            if not doc:
                return None

            doc.pop("_id", None)

            return Company(**doc)

        except Exception as e:

            logger.exception(f"Error loading company: {e}")

            return None

    async def is_allowed(
        self,
        company_id: Optional[str],
        service: ServiceType,
    ) -> Tuple[bool, Optional[str]]:
        """
        Returns (allowed, denial_message).
        If company_id is None or "GUEST", all services are allowed.
        """
        if not company_id:
            company_id = "guest-000"

        company = await self.get_company(company_id)

        if company is None:

            return (
                False,
                "Company not found."
            )

        if service in company.allowed_services:
            return True, None

        return False, (
            f"Your company **{company.name}** subscription does not include "
            f"**{service.value.capitalize()}** booking. "
            f"Available services: {', '.join(s.value for s in company.allowed_services)}. "
            f"Please contact your travel administrator to upgrade."
        )

    async def get_allowed_services(self, company_id: Optional[str]) -> List[ServiceType]:
        if not company_id:
            return list(ServiceType)
        company = await self.get_company(company_id)
        return company.allowed_services if company else list(ServiceType)

    async def upsert_company(self, company: Company) -> None:
        """Create or update a company record."""
        db = get_db()
        await db.companies.update_one(
            {"company_id": company.company_id},
            {"$set": company.dict()},
            upsert=True,
        )
        logger.info(f"Company upserted: {company.name}")


permission_service = PermissionService()
