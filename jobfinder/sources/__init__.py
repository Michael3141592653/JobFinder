from jobfinder.sources import greenhouse, lever

# source name -> async fetch(client, board) -> list[Job]
FETCHERS = {
    "greenhouse": greenhouse.fetch,
    "lever": lever.fetch,
}
