from opensearchpy import OpenSearch
from .. import config


def create_client(url: str | None = None) -> OpenSearch:
    target = url or config.opensearch_url()
    return OpenSearch(hosts=[target], http_compress=True)
