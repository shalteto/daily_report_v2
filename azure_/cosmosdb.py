# pip install azure-cosmos
# pip install python-dotenv
from azure.cosmos import CosmosClient
from dotenv import load_dotenv
import os
import uuid

# .envファイルの読み込み
load_dotenv()


class CosmosDBClient:
    def __init__(
        self,
        endpoint=None,
        key=None,
        database_name="sat-db",
        container_name="main_container",
    ):
        self.endpoint = endpoint or os.getenv("COSMOSDB_ENDPOINT")
        self.key = key or os.getenv("COSMOSDB_KEY")
        self.database_name = database_name
        self.container_name = container_name
        self.client = CosmosClient(self.endpoint, self.key)
        self.database = self.client.get_database_client(self.database_name)
        self.container = self.database.get_container_client(self.container_name)

    def upsert_to_container(self, data):
        # データがリストの場合は複数レコードを登録
        if isinstance(data, list):
            for record in data:
                self.container.upsert_item(body=record)
            return f"{len(data)} 件のデータを登録しました"

        # 単一レコードの場合
        if "id" not in data:
            data["id"] = str(uuid.uuid4())
        return self.container.upsert_item(body=data)

    def search_container_by_query(self, query: str, parameters: list):
        results = self.container.query_items(
            query=query, parameters=parameters, enable_cross_partition_query=True
        )
        return list(results)

    def delete_item_from_container(self, item_id: str, category: str):
        """
        指定したidとcategory（パーティションキー）のレコードを削除します。
        """
        self.container.delete_item(item=item_id, partition_key=category)
        return f"id={item_id}, category={category} のレコードを削除しました"
