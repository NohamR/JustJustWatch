import requests
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from pprint import pprint
import json
from tqdm import tqdm
from tabulate import tabulate
from simple_term_menu import TerminalMenu

def country_code_to_flag(code):
        return chr(127462 + ord(code[0]) - ord('A')) + chr(127462 + ord(code[1]) - ord('A'))

def format_countries(country_codes):
    representative_flags = ["FR", "GB", "US", "DE"]
    selected_countries = [code for code in country_codes if code in representative_flags]
    
    if len(selected_countries) < len(representative_flags):
        selected_countries += [code for code in country_codes if code not in selected_countries][:4-len(selected_countries)]
    
    if len(country_codes) > len(selected_countries):
        return ', '.join([f"{country_code_to_flag(code)} {code}" for code in selected_countries]) + f" + {len(country_codes) - len(selected_countries)} more"
    else:
        return ', '.join([f"{country_code_to_flag(code)} {code}" for code in selected_countries])

def update_url_query(url):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    keys_to_remove = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content']
    for key in keys_to_remove:
        query_params.pop(key, None)
    query_params.update(query_params)
    new_query_string = urlencode(query_params, doseq=True)
    new_url = urlunparse((
        parsed_url.scheme,
        parsed_url.netloc,
        parsed_url.path,
        parsed_url.params,
        new_query_string,
        parsed_url.fragment
    ))    
    return new_url

def search(query):
    headers = {'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',}
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
        "query": "query GetSuggestedTitles($country: Country!, $language: Language!, $first: Int!, $filter: TitleFilter) {\n  popularTitles(country: $country, first: $first, filter: $filter) {\n    edges {\n      node {\n        ...SuggestedTitle\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment SuggestedTitle on MovieOrShow {\n  __typename\n  id\n  objectType\n  objectId\n  content(country: $country, language: $language) {\n    fullPath\n    title\n    originalReleaseYear\n    posterUrl\n    fullPath\n    __typename\n  }\n  watchNowOffer(country: $country, platform: WEB) {\n    id\n    standardWebURL\n    package {\n      id\n      packageId\n      __typename\n    }\n    __typename\n  }\n  offers(country: $country, platform: WEB) {\n    monetizationType\n    presentationType\n    standardWebURL\n    package {\n      id\n      packageId\n      __typename\n    }\n    id\n    __typename\n  }\n}\n",
    }
    response = requests.post('https://apis.justwatch.com/graphql', headers=headers, json=json_data).json()
    options = []
    for title in response['data']['popularTitles']['edges']:
        title = title['node']
        contentTitle = title['content']['title']
        contentPath = title['content']['fullPath']
        objectType = title['objectType']
        originalReleaseYear = title['content']['originalReleaseYear']
        slug = f"{contentTitle} ({objectType}) - {originalReleaseYear}"
        if contentPath == '':
            slug += ' - Unavailable ' + chr(0x1F6A7)
        options.append({'title': contentTitle, 'path': contentPath, 'objectType': objectType, 'originalReleaseYear': originalReleaseYear, 'slug': slug})
    options_slug = [option['slug'] for option in options]
    terminal_menu = TerminalMenu(options_slug)
    nameselected = options[terminal_menu.show()]
    if nameselected['path'] == '':
        print('This title is unavailable')
    else:
        print(f"Selected: {nameselected['slug']} - {'https://www.justwatch.com' + nameselected['path']}")
        path = nameselected['path']
        fetchdata(path)


def fetchdata(path):
    headers = {'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',}
    countries = [country['iso_3166_2'] for country in requests.get('https://apis.justwatch.com/content/locales/state', headers=headers).json()]
    print(f"Got {len(countries)} countries")
    SERVICES = {}
    IDS = []
    for country in tqdm(countries):
        json_data = {
            'operationName': 'GetUrlTitleDetails',
            'variables': {
                'platform': 'WEB',
                'fullPath': path,
                'language': 'fr',
                'country': country,
                'episodeMaxLimit': 100,
            },
            'query': 'query GetUrlTitleDetails($fullPath: String!, $country: Country!, $language: Language!, $episodeMaxLimit: Int, $platform: Platform! = WEB, $allowSponsoredRecommendations: SponsoredRecommendationsInput, $format: ImageFormat, $backdropProfile: BackdropProfile, $streamingChartsFilter: StreamingChartsFilter) {\n  urlV2(fullPath: $fullPath) {\n    id\n    metaDescription\n    metaKeywords\n    metaRobots\n    metaTitle\n    heading1\n    heading2\n    htmlContent\n    node {\n      ...TitleDetails\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment TitleDetails on Node {\n  id\n  __typename\n  ... on MovieOrShowOrSeason {\n    plexPlayerOffers: offers(\n      country: $country\n      platform: $platform\n      filter: {packages: ["pxp"]}\n    ) {\n      id\n      standardWebURL\n      package {\n        id\n        packageId\n        clearName\n        technicalName\n        shortName\n        __typename\n      }\n      __typename\n    }\n    maxOfferUpdatedAt(country: $country, platform: WEB)\n    appleOffers: offers(\n      country: $country\n      platform: $platform\n      filter: {packages: ["atp", "itu"]}\n    ) {\n      ...TitleOffer\n      __typename\n    }\n    disneyOffersCount: offerCount(\n      country: $country\n      platform: $platform\n      filter: {packages: ["dnp"]}\n    )\n    starOffersCount: offerCount(\n      country: $country\n      platform: $platform\n      filter: {packages: ["srp"]}\n    )\n    objectType\n    objectId\n    offerCount(country: $country, platform: $platform)\n    uniqueOfferCount: offerCount(\n      country: $country\n      platform: $platform\n      filter: {bestOnly: true}\n    )\n    offers(country: $country, platform: $platform) {\n      monetizationType\n      elementCount\n      package {\n        id\n        packageId\n        clearName\n        __typename\n      }\n      __typename\n    }\n    watchNowOffer(country: $country, platform: $platform) {\n      id\n      standardWebURL\n      __typename\n    }\n    promotedBundles(country: $country, platform: $platform) {\n      promotionUrl\n      __typename\n    }\n    availableTo(country: $country, platform: $platform) {\n      availableCountDown(country: $country)\n      availableToDate\n      package {\n        id\n        shortName\n        __typename\n      }\n      __typename\n    }\n    fallBackClips: content(country: $country, language: "en") {\n      clips {\n        ...TrailerClips\n        __typename\n      }\n      videobusterClips: clips(providers: [VIDEOBUSTER]) {\n        ...TrailerClips\n        __typename\n      }\n      dailymotionClips: clips(providers: [DAILYMOTION]) {\n        ...TrailerClips\n        __typename\n      }\n      __typename\n    }\n    content(country: $country, language: $language) {\n      backdrops {\n        backdropUrl\n        __typename\n      }\n      fullBackdrops: backdrops(profile: S1920, format: JPG) {\n        backdropUrl\n        __typename\n      }\n      clips {\n        ...TrailerClips\n        __typename\n      }\n      videobusterClips: clips(providers: [VIDEOBUSTER]) {\n        ...TrailerClips\n        __typename\n      }\n      dailymotionClips: clips(providers: [DAILYMOTION]) {\n        ...TrailerClips\n        __typename\n      }\n      externalIds {\n        imdbId\n        __typename\n      }\n      fullPath\n      posterUrl\n      fullPosterUrl: posterUrl(profile: S718, format: JPG)\n      runtime\n      isReleased\n      scoring {\n        imdbScore\n        imdbVotes\n        tmdbPopularity\n        tmdbScore\n        jwRating\n        tomatoMeter\n        certifiedFresh\n        __typename\n      }\n      shortDescription\n      title\n      originalReleaseYear\n      originalReleaseDate\n      upcomingReleases(releaseTypes: DIGITAL) {\n        releaseCountDown(country: $country)\n        releaseDate\n        label\n        package {\n          id\n          packageId\n          shortName\n          clearName\n          icon(profile: S100)\n          hasRectangularIcon(country: $country, platform: WEB)\n          __typename\n        }\n        __typename\n      }\n      genres {\n        shortName\n        translation(language: $language)\n        __typename\n      }\n      subgenres {\n        content(country: $country, language: $language) {\n          shortName\n          name\n          __typename\n        }\n        __typename\n      }\n      ... on MovieOrShowOrSeasonContent {\n        subgenres {\n          content(country: $country, language: $language) {\n            url: moviesUrl {\n              fullPath\n              __typename\n            }\n            __typename\n          }\n          __typename\n        }\n        __typename\n      }\n      ... on MovieOrShowContent {\n        originalTitle\n        ageCertification\n        credits {\n          role\n          name\n          characterName\n          personId\n          __typename\n        }\n        interactions {\n          dislikelistAdditions\n          likelistAdditions\n          votesNumber\n          __typename\n        }\n        productionCountries\n        __typename\n      }\n      ... on SeasonContent {\n        seasonNumber\n        interactions {\n          dislikelistAdditions\n          likelistAdditions\n          votesNumber\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    popularityRank(country: $country) {\n      rank\n      trend\n      trendDifference\n      __typename\n    }\n    streamingCharts(country: $country, filter: $streamingChartsFilter) {\n      edges {\n        streamingChartInfo {\n          rank\n          trend\n          trendDifference\n          updatedAt\n          daysInTop10\n          daysInTop100\n          daysInTop1000\n          daysInTop3\n          topRank\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  ... on MovieOrShowOrSeason {\n    likelistEntry {\n      createdAt\n      __typename\n    }\n    dislikelistEntry {\n      createdAt\n      __typename\n    }\n    __typename\n  }\n  ... on MovieOrShow {\n    watchlistEntryV2 {\n      createdAt\n      __typename\n    }\n    customlistEntries {\n      createdAt\n      genericTitleList {\n        id\n        __typename\n      }\n      __typename\n    }\n    similarTitlesV2(\n      country: $country\n      allowSponsoredRecommendations: $allowSponsoredRecommendations\n    ) {\n      sponsoredAd {\n        ...SponsoredAd\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  ... on Movie {\n    permanentAudiences\n    seenlistEntry {\n      createdAt\n      __typename\n    }\n    __typename\n  }\n  ... on Show {\n    permanentAudiences\n    totalSeasonCount\n    seenState(country: $country) {\n      progress\n      seenEpisodeCount\n      __typename\n    }\n    tvShowTrackingEntry {\n      createdAt\n      __typename\n    }\n    seasons(sortDirection: DESC) {\n      id\n      objectId\n      objectType\n      totalEpisodeCount\n      availableTo(country: $country, platform: $platform) {\n        availableToDate\n        availableCountDown(country: $country)\n        package {\n          id\n          shortName\n          __typename\n        }\n        __typename\n      }\n      content(country: $country, language: $language) {\n        posterUrl\n        seasonNumber\n        fullPath\n        title\n        upcomingReleases(releaseTypes: DIGITAL) {\n          releaseDate\n          releaseCountDown(country: $country)\n          package {\n            id\n            shortName\n            __typename\n          }\n          __typename\n        }\n        isReleased\n        originalReleaseYear\n        __typename\n      }\n      show {\n        id\n        objectId\n        objectType\n        watchlistEntryV2 {\n          createdAt\n          __typename\n        }\n        content(country: $country, language: $language) {\n          title\n          __typename\n        }\n        __typename\n      }\n      fallBackClips: content(country: $country, language: "en") {\n        clips {\n          ...TrailerClips\n          __typename\n        }\n        videobusterClips: clips(providers: [VIDEOBUSTER]) {\n          ...TrailerClips\n          __typename\n        }\n        dailymotionClips: clips(providers: [DAILYMOTION]) {\n          ...TrailerClips\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    recentEpisodes: episodes(\n      sortDirection: DESC\n      limit: 3\n      releasedInCountry: $country\n    ) {\n      ...Episode\n      __typename\n    }\n    __typename\n  }\n  ... on Season {\n    totalEpisodeCount\n    episodes(limit: $episodeMaxLimit) {\n      ...Episode\n      __typename\n    }\n    show {\n      id\n      objectId\n      objectType\n      totalSeasonCount\n      customlistEntries {\n        createdAt\n        genericTitleList {\n          id\n          __typename\n        }\n        __typename\n      }\n      tvShowTrackingEntry {\n        createdAt\n        __typename\n      }\n      fallBackClips: content(country: $country, language: "en") {\n        clips {\n          ...TrailerClips\n          __typename\n        }\n        videobusterClips: clips(providers: [VIDEOBUSTER]) {\n          ...TrailerClips\n          __typename\n        }\n        dailymotionClips: clips(providers: [DAILYMOTION]) {\n          ...TrailerClips\n          __typename\n        }\n        __typename\n      }\n      content(country: $country, language: $language) {\n        title\n        ageCertification\n        fullPath\n        genres {\n          shortName\n          __typename\n        }\n        credits {\n          role\n          name\n          characterName\n          personId\n          __typename\n        }\n        productionCountries\n        externalIds {\n          imdbId\n          __typename\n        }\n        upcomingReleases(releaseTypes: DIGITAL) {\n          releaseDate\n          __typename\n        }\n        backdrops {\n          backdropUrl\n          __typename\n        }\n        posterUrl\n        isReleased\n        videobusterClips: clips(providers: [VIDEOBUSTER]) {\n          ...TrailerClips\n          __typename\n        }\n        dailymotionClips: clips(providers: [DAILYMOTION]) {\n          ...TrailerClips\n          __typename\n        }\n        __typename\n      }\n      seenState(country: $country) {\n        progress\n        __typename\n      }\n      watchlistEntryV2 {\n        createdAt\n        __typename\n      }\n      dislikelistEntry {\n        createdAt\n        __typename\n      }\n      likelistEntry {\n        createdAt\n        __typename\n      }\n      similarTitlesV2(\n        country: $country\n        allowSponsoredRecommendations: $allowSponsoredRecommendations\n      ) {\n        sponsoredAd {\n          ...SponsoredAd\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    seenState(country: $country) {\n      progress\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment TitleOffer on Offer {\n  id\n  presentationType\n  monetizationType\n  retailPrice(language: $language)\n  retailPriceValue\n  currency\n  lastChangeRetailPriceValue\n  type\n  package {\n    id\n    packageId\n    clearName\n    technicalName\n    icon(profile: S100)\n    planOffers(country: $country, platform: WEB) {\n      title\n      retailPrice(language: $language)\n      isTrial\n      durationDays\n      retailPriceValue\n      children {\n        title\n        retailPrice(language: $language)\n        isTrial\n        durationDays\n        retailPriceValue\n        __typename\n      }\n      __typename\n    }\n    hasRectangularIcon(country: $country, platform: WEB)\n    __typename\n  }\n  standardWebURL\n  elementCount\n  availableTo\n  deeplinkRoku: deeplinkURL(platform: ROKU_OS)\n  subtitleLanguages\n  videoTechnology\n  audioTechnology\n  audioLanguages(language: $language)\n  __typename\n}\n\nfragment TrailerClips on Clip {\n  sourceUrl\n  externalId\n  provider\n  name\n  __typename\n}\n\nfragment SponsoredAd on SponsoredRecommendationAd {\n  bidId\n  holdoutGroup\n  campaign {\n    name\n    externalTrackers {\n      type\n      data\n      __typename\n    }\n    hideRatings\n    hideDetailPageButton\n    promotionalImageUrl\n    promotionalVideo {\n      url\n      __typename\n    }\n    promotionalTitle\n    promotionalText\n    promotionalProviderLogo\n    watchNowLabel\n    watchNowOffer {\n      standardWebURL\n      presentationType\n      monetizationType\n      package {\n        id\n        packageId\n        shortName\n        clearName\n        icon\n        __typename\n      }\n      __typename\n    }\n    nodeOverrides {\n      nodeId\n      promotionalImageUrl\n      watchNowOffer {\n        standardWebURL\n        __typename\n      }\n      __typename\n    }\n    node {\n      nodeId: id\n      __typename\n      ... on MovieOrShowOrSeason {\n        content(country: $country, language: $language) {\n          fullPath\n          posterUrl\n          title\n          originalReleaseYear\n          scoring {\n            imdbScore\n            __typename\n          }\n          externalIds {\n            imdbId\n            __typename\n          }\n          backdrops(format: $format, profile: $backdropProfile) {\n            backdropUrl\n            __typename\n          }\n          isReleased\n          __typename\n        }\n        objectId\n        objectType\n        offers(country: $country, platform: $platform) {\n          monetizationType\n          presentationType\n          package {\n            id\n            packageId\n            __typename\n          }\n          id\n          __typename\n        }\n        __typename\n      }\n      ... on MovieOrShow {\n        watchlistEntryV2 {\n          createdAt\n          __typename\n        }\n        __typename\n      }\n      ... on Show {\n        seenState(country: $country) {\n          seenEpisodeCount\n          __typename\n        }\n        __typename\n      }\n      ... on Season {\n        content(country: $country, language: $language) {\n          seasonNumber\n          __typename\n        }\n        show {\n          __typename\n          id\n          content(country: $country, language: $language) {\n            originalTitle\n            __typename\n          }\n          watchlistEntryV2 {\n            createdAt\n            __typename\n          }\n        }\n        __typename\n      }\n      ... on GenericTitleList {\n        followedlistEntry {\n          createdAt\n          name\n          __typename\n        }\n        id\n        type\n        content(country: $country, language: $language) {\n          name\n          visibility\n          __typename\n        }\n        titles(country: $country, first: 40) {\n          totalCount\n          edges {\n            cursor\n            node: nodeV2 {\n              content(country: $country, language: $language) {\n                fullPath\n                posterUrl\n                title\n                originalReleaseYear\n                scoring {\n                  imdbScore\n                  __typename\n                }\n                isReleased\n                __typename\n              }\n              id\n              objectId\n              objectType\n              __typename\n            }\n            __typename\n          }\n          __typename\n        }\n        __typename\n      }\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment Episode on Episode {\n  id\n  objectId\n  objectType\n  seenlistEntry {\n    createdAt\n    __typename\n  }\n  content(country: $country, language: $language) {\n    title\n    shortDescription\n    episodeNumber\n    seasonNumber\n    isReleased\n    runtime\n    upcomingReleases {\n      releaseDate\n      label\n      package {\n        id\n        packageId\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n',
        }
        response = requests.post('https://apis.justwatch.com/graphql', headers=headers, json=json_data).json()
        # last_updated = response['data']['urlV2']['node']['maxOfferUpdatedAt']
        # print('last_updated: ', last_updated)
        for offer in response['data']['urlV2']['node']['plexPlayerOffers']:
            service = offer['package']['clearName']
            url = update_url_query(offer['standardWebURL'])
            id = offer['package']['id']
            if id not in IDS:
                IDS.append(id)
                infos = {'id': id,'service': service,'url': url,'countries': [country],}
                SERVICES[service] = infos
            else:
                if country not in SERVICES[service]['countries']:
                    SERVICES[service]['countries'].append(country)

    table_data = []
    for service, details in SERVICES.items():
        formatted_countries = format_countries(details["countries"])
        table_data.append([details["service"], formatted_countries, details["url"]])

    headers = ["Service", "Countries", "URL"]
    print(tabulate(table_data, headers, tablefmt="grid"))
    return SERVICES

# url = 'https://www.justwatch.com/fr/serie/mad-dogs' # /fr/serie/mad-dogs
# url = input('Enter the URL: ')
# path = url.replace('https://www.justwatch.com', '')
# services = fetchdata(path)
# with open('services.json', 'w') as f:
#     json.dump(services, f, indent=4)

query = input('Enter the query: ')
search(query)