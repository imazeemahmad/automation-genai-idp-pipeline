from models.procurement import Procurement
from repositories.coupa_repository import CoupaRepository


def test_search_procurements_returns_procurement_list_from_ids():
    # Given
    repository = CoupaRepository()
    ids = ["P001", "P002", "P003"]

    # When
    result = repository.search_procurements(ids)

    # Then
    assert len(result) == 3
    assert all(isinstance(item, Procurement) for item in result)
    assert [item.id for item in result] == ["P001", "P002", "P003"]
    assert [item.name for item in result] == ["P-P001", "P-P002", "P-P003"]
