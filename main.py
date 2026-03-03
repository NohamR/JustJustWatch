import requests
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from tqdm import tqdm
from tabulate import tabulate
from InquirerPy import inquirer
from InquirerPy.base.control import Choice


def country_code_to_flag(code):
    return chr(127462 + ord(code[0]) - ord("A")) + chr(127462 + ord(code[1]) - ord("A"))


def format_countries(country_codes):
    representative_flags = ["FR", "GB", "US", "DE"]
    selected_countries = [
        code for code in country_codes if code in representative_flags
    ]

    if len(selected_countries) < len(representative_flags):
        selected_countries += [
            code for code in country_codes if code not in selected_countries
        ][: 4 - len(selected_countries)]

    if len(country_codes) > len(selected_countries):
        return (
            ", ".join(
                [f"{country_code_to_flag(code)} {code}" for code in selected_countries]
            )
            + f" + {len(country_codes) - len(selected_countries)} more"
        )
    else:
        return ", ".join(
            [f"{country_code_to_flag(code)} {code}" for code in selected_countries]
        )


def update_url_query(url):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    keys_to_remove = [
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
    ]
    for key in keys_to_remove:
        query_params.pop(key, None)
    new_query_string = urlencode(query_params, doseq=True)
    return urlunparse(
        (
            parsed_url.scheme,
            parsed_url.netloc,
            parsed_url.path,
            parsed_url.params,
            new_query_string,
            parsed_url.fragment,
        )
    )


def search(query):
    headers = {
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    }
    json_data = {
        "operationName": "GetSuggestedTitles",
        "variables": {
            "country": "US",
            "language": "en",
            "first": 5,
            "filter": {
                "searchQuery": query,
                "includeTitlesWithoutUrl": True,
            },
        },
        "query": "query GetSuggestedTitles($country: Country!, $language: Language!, $first: Int!, $filter: TitleFilter) {\n  popularTitles(country: $country, first: $first, filter: $filter) {\n    edges {\n      node {\n        ...SuggestedTitle\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment SuggestedTitle on MovieOrShow {\n  __typename\n  id\n  objectType\n  objectId\n  content(country: $country, language: $language) {\n    fullPath\n    title\n    originalReleaseYear\n    posterUrl\n    __typename\n  }\n  watchNowOffer(country: $country, platform: WEB) {\n    id\n    standardWebURL\n    package {\n      id\n      packageId\n      __typename\n    }\n    __typename\n  }\n  offers(country: $country, platform: WEB) {\n    monetizationType\n    presentationType\n    standardWebURL\n    package {\n      id\n      packageId\n      __typename\n    }\n    id\n    __typename\n  }\n}\n",
    }

    response = requests.post(
        "https://apis.justwatch.com/graphql", headers=headers, json=json_data
    ).json()
    choices = []

    for edge in response["data"]["popularTitles"]["edges"]:
        node = edge["node"]
        content = node["content"]
        slug = f"{content['title']} ({node['objectType']}) - {content['originalReleaseYear']}"

        if content["fullPath"] == "":
            slug += " - Unavailable 🚧"

        choices.append(Choice(value=node, name=slug))

    if not choices:
        print("No results found.")
        return

    selected_node = inquirer.fuzzy(
        message="Select a title:",
        choices=choices,
        match_exact=True,
    ).execute()

    path = selected_node["content"]["fullPath"]
    if path == "":
        print("This title is unavailable")
    else:
        print(
            f"Selected: {selected_node['content']['title']} - https://www.justwatch.com{path}"
        )
        fetchdata(path)


def fetchdata(path):
    headers = {
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    }
    countries = [
        country["iso_3166_2"]
        for country in requests.get(
            "https://apis.justwatch.com/content/locales/state", headers=headers
        ).json()
    ]

    print(f"Checking {len(countries)} countries...")
    SERVICES = {}
    IDS = []

    query_str = 'query GetUrlTitleDetails($fullPath: String!, $country: Country!, $language: Language!, $episodeMaxLimit: Int, $platform: Platform! = WEB, $allowSponsoredRecommendations: SponsoredRecommendationsInput, $format: ImageFormat, $backdropProfile: BackdropProfile, $streamingChartsFilter: StreamingChartsFilter) {\n  urlV2(fullPath: $fullPath) {\n    node {\n      ...TitleDetails\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment TitleDetails on Node {\n  ... on MovieOrShowOrSeason {\n    plexPlayerOffers: offers(country: $country, platform: $platform, filter: {packages: ["pxp"]}) {\n      id\n      standardWebURL\n      package { id packageId clearName technicalName shortName __typename }\n      __typename\n    }\n  }\n}'

    for country in tqdm(countries, desc="Fetching Availability"):
        json_data = {
            "operationName": "GetUrlTitleDetails",
            "variables": {
                "platform": "WEB",
                "fullPath": path,
                "language": "fr",
                "country": country,
                "episodeMaxLimit": 100,
            },
            "query": query_str,
        }

        try:
            res = requests.post(
                "https://apis.justwatch.com/graphql", headers=headers, json=json_data
            ).json()
            offers = (
                res.data["urlV2"]["node"].get("plexPlayerOffers", [])
                if res.get("data")
                else []
            )

            for offer in offers:
                service = offer["package"]["clearName"]
                url = update_url_query(offer["standardWebURL"])
                pkg_id = offer["package"]["id"]

                if pkg_id not in IDS:
                    IDS.append(pkg_id)
                    SERVICES[service] = {
                        "id": pkg_id,
                        "service": service,
                        "url": url,
                        "countries": [country],
                    }
                else:
                    if country not in SERVICES[service]["countries"]:
                        SERVICES[service]["countries"].append(country)
        except:
            continue

    if not SERVICES:
        print("\nNo Plex/Free offers found globally.")
        return

    table_data = [
        [details["service"], format_countries(details["countries"]), details["url"]]
        for details in SERVICES.values()
    ]
    print(
        "\n"
        + tabulate(table_data, headers=["Service", "Countries", "URL"], tablefmt="grid")
    )


if __name__ == "__main__":
    user_query = inquirer.text(message="Enter the movie/show to search:").execute()
    if user_query:
        search(user_query)
