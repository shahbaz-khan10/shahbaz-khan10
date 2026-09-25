from authentication.models import User
from masters.models import Currency, ExchangeRate


class TestCurrencyCrud:
    def test_create_and_list(self, auth_client):
        res = auth_client["client"].post(
            "/api/currencies",
            data={"code": "SGD", "name": "Singapore Dollar", "symbol": "S$"},
            content_type="application/json",
        )
        assert res.status_code == 200, res.content
        body = res.json()
        assert body["code"] == "SGD"

        res = auth_client["client"].get("/api/currencies")
        assert res.status_code == 200
        assert res.json()["pagination"]["total"] == 1
        assert res.json()["items"][0]["name"] == "Singapore Dollar"

    def test_patch_and_uppercase(self, auth_client):
        res = auth_client["client"].post(
            "/api/currencies",
            data={"code": "eur", "name": "Euro"},
            content_type="application/json",
        )
        assert res.status_code == 200
        assert res.json()["code"] == "EUR"

        pk = res.json()["id"]
        res = auth_client["client"].patch(
            f"/api/currencies/{pk}",
            data={"name": "Euro Changed"},
            content_type="application/json",
        )
        assert res.status_code == 200
        assert res.json()["name"] == "Euro Changed"

    def test_duplicate_code_is_400(self, auth_client):
        auth_client["client"].post(
            "/api/currencies",
            data={"code": "PKR", "name": "Pakistani Rupee"},
            content_type="application/json",
        )
        res = auth_client["client"].post(
            "/api/currencies",
            data={"code": "PKR", "name": "Duplicate"},
            content_type="application/json",
        )
        assert res.status_code == 400

    def test_soft_delete_and_audit(self, auth_client):
        res = auth_client["client"].post(
            "/api/currencies",
            data={"code": "BHD", "name": "Bahraini Dinar"},
            content_type="application/json",
        )
        pk = res.json()["id"]
        res = auth_client["client"].delete(f"/api/currencies/{pk}")
        assert res.status_code == 200

        obj = Currency.objects.all_objects().get(pk=pk)
        assert obj.is_deleted is True
        assert not Currency.objects.filter(pk=pk).exists()


class TestExchangeRate:
    def test_same_currency_pair_rejected(self, auth_client, db):
        from masters.models import Currency

        usd = Currency.objects.create(code="USD", name="US Dollar")
        res = auth_client["client"].post(
            "/api/exchange-rates",
            data={
                "from_currency_id": usd.id,
                "to_currency_id": usd.id,
                "rate": "1.0",
                "effective_date": "2026-01-01",
            },
            content_type="application/json",
        )
        assert res.status_code == 400

    def test_duplicate_pair_date_rejected(self, auth_client, db):
        from masters.models import Currency

        usd = Currency.objects.create(code="USD", name="US Dollar")
        pkr = Currency.objects.create(code="PKR", name="Pakistani Rupee")
        payload = {
            "from_currency_id": usd.id,
            "to_currency_id": pkr.id,
            "rate": "278.5",
            "effective_date": "2026-01-01",
        }
        res = auth_client["client"].post("/api/exchange-rates", data=payload, content_type="application/json")
        assert res.status_code == 200
        res = auth_client["client"].post("/api/exchange-rates", data=payload, content_type="application/json")
        assert res.status_code == 400


class TestItemValidation:
    def test_item_requires_category_and_unit(self, auth_client, db):
        res = auth_client["client"].post(
            "/api/items",
            data={"code": "FAB001", "name": "Cotton Fabric"},
            content_type="application/json",
        )
        assert res.status_code == 422

    def test_item_create_with_fks(self, auth_client, db):
        from masters.models import ItemCategory, UnitOfMeasure

        cat = ItemCategory.objects.create(code="FAB", name="Fabric")
        unit = UnitOfMeasure.objects.create(code="MTR", name="Meter", dimension="length")
        res = auth_client["client"].post(
            "/api/items",
            data={"code": "FAB-001", "name": "Cotton Poplin", "category_id": cat.id, "unit_id": unit.id, "purchase_price": "2.5"},
            content_type="application/json",
        )
        assert res.status_code == 200, res.content
        body = res.json()
        assert body["category_name"] == "Fabric"
        assert body["unit_code"] == "MTR"


class TestSizeGroup:
    def test_create_with_sizes(self, auth_client, db):
        from masters.models import Size

        s1 = Size.objects.create(code="S", name="Small", sort_order=1)
        s2 = Size.objects.create(code="M", name="Medium", sort_order=2)
        res = auth_client["client"].post(
            "/api/size-groups",
            data={"name": "Core", "size_ids": [s1.id, s2.id]},
            content_type="application/json",
        )
        assert res.status_code == 200, res.content
        body = res.json()
        assert len(body["sizes"]) == 2
        assert [s["code"] for s in body["sizes"]] == ["S", "M"]