from models.procurement import Procurement


class CoupaRepository:
    def search_procurements(self, ids: list[str] | None) -> list[Procurement]:
        if ids is None:
            return []

        return [
            Procurement(id=procurement_id, name=f"P-{procurement_id}")
            for procurement_id in ids
        ]
