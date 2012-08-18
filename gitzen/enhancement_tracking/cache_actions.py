from datetime import datetime, timedelta

import requests
from requests.exceptions import RequestException

from django.core.cache import cache

# Constant URL string for accessing GitHub issues through the GitHub API. It
# requires a GitHub organization/user and repository for the string's
# formatting.
GIT_ISSUE_URL = 'https://api.github.com/repos/%(organization)s/' \
                '%(repository)s/issues'

# Constant URL string for accessing individual GitHub issue through the GitHub
# API. It requires a GitHub organization/user, repository, and issue number for
# the string's formatting.
GIT_INDIVIDUAL_ISSUE_URL = 'https://api.github.com/repos/%(organization)s/' \
                           '%(repository)s/issues/%(issue_number)i'

# Constant URL string for searching for tickets through the Zendesk API. It
# requires the custom URL subdomain of the specific company whose information
# is being accessed for the string's formatting.
ZEN_SEARCH_URL = 'https://%(subdomain)s.zendesk.com/api/v2/search.json'

# Constant search query used to access all open Zendesk tickets with the
# product_enhancement tag form its API.
ZEN_TICKET_ALL_SEARCH_QUERY = 'type:ticket tags:product_enhancement status:open'

# Constant search query used to access open Zendesk tickets with the
# product_enhancement tag that have been updated since a certain date. The
# expected format for the date is YYYY-MM-DD.
ZEN_TICKET_UPDATE_SEARCH_QUERY = 'type:ticket tags:product_enhancement ' \
                                 'updated>%(updated)s'

# Constant URL string for accessing Zendesk users through the Zendesk API. It
# requires the custom URL subdomain for the specific company whose users are
# being accessed and the ID number of the user being accessed for the string's
# formatting.
ZEN_USER_URL = 'https://%(subdomain)s.zendesk.com/api/v2/users/%(user_id)i.json'

def build_cache_index(api_access_data):
    """Builds and indexes the cache data necessary for the application for the
    passed API access model.

    Parameters:
        api_access_data - The object that contains the necessary access
                            parameters for getting the data needed for the
                            application from the Zendesk and GitHub APIs.

    This function will raise any RequestExceptions that happen while trying to
    access either the Zendesk or GitHub APIs so they can be properly handled by
    the calling view function.
    """
    cache_data = {} # Data to be stored in the cache for the passed API access
                    # model.
    zen_tickets = [] # List of the open tickets in Zendesk with the API access
                     # model's specified tags.
    zen_user_reference = {} # Dictionary reference of the user IDs and
                            # user names associated with the Zendesk tickets in
                            # zen_tickets.
    git_tickets = [] # List of the GitHub tickets associated with the Zendesk
                     # tickets in zen_tickets.
    zen_fieldid = api_access_data.zen_fieldid

    try:
        zen_tickets = get_zen_tickets(api_access_data)
        zen_user_ids, git_issue_numbers = get_id_lists(zen_tickets,
                                                       zen_fieldid)
        cache_data['git_issue_numbers'] = git_issue_numbers
        zen_user_reference = get_zen_users(api_access_data, zen_user_ids)
        cache_data['zen_user_reference'] = zen_user_reference
        git_tickets = get_git_tickets(api_access_data, git_issue_numbers)
        cache_data['git_tickets'] = git_tickets
    except RequestException:
        # Raise RequestExceptions so they can be properly handled by whatever
        # view function call the build_cache_index function.
        raise

    enhancement_data = build_enhancement_data(zen_tickets, zen_user_reference,
                                              git_tickets, zen_fieldid)
    cache_data = dict(cache_data.items() + enhancement_data.items())

    # Subtract 10 minutes from the actual time to ensure that no updates are
    # left out if they were made during the time the function was processing.
    cache_data['last_updated'] = datetime.utcnow() - timedelta(minutes=10)
    cache.set(api_access_data.id, cache_data)

def get_zen_tickets(api_access_data):
    """Gets all of the open product_enhancement Zendesk tickets using the
    Zendesk API.

    Parameters:
        api_access_data - The object that contains the current user's API
                            access data necessary to access the tickets on their
                            Zendesk account.

    Returns a gathered list of Zendesk tickets.
    """
    # Zendesk user email set up for API token authorization
    zen_name_tk = api_access_data.zen_name + '/token'
    zen_tickets = []
    page = 1

    try:
        while True:
            request_zen_tickets = requests.get(
                ZEN_SEARCH_URL % {'subdomain': api_access_data.zen_url},
                params={'query': ZEN_TICKET_ALL_SEARCH_QUERY,
                        'per_page': 100,
                        'page': page},
                auth=(zen_name_tk, api_access_data.zen_token)
            )
            if request_zen_tickets.status_code != 200:
                request_zen_tickets.raise_for_status()
            zen_tickets.extend(request_zen_tickets.json['results'])
            if request_zen_tickets.json['next_page'] is not None:
                page += 1
            else:
                break

    # Catches exceptions from requests.get() or raise_for_status()
    except RequestException as e:
        # Redefines the args attribute of the exception to contain both the
        # original error message and the name of the API responsible for causing
        # the exception.
        e.args = (e.args[0], 'Zendesk')

        # Raise the exception so it can be caught by the except in the calling
        # function for further processing.
        raise

    return zen_tickets

def get_id_lists(zen_tickets, zen_fieldid):
    """Gets lists of the Zendesk user IDs and the GitHub issue numbers that are
    associated with the passed list of Zendesk tickets.

    Parameters:
        zen_tickets - A list of Zendesk tickets whose associated GitHub issue
                    numbers and Zendesk user IDs are desired.
        zen_fieldid - The ID number of the custom field in Zendesk tickets that
                        holds its associated GitHub issue number.

    Returns a tuple of two value with the first being the gathered list of
    associated Zendesk user IDs and with the second being the gathered list
    of associated GitHub issue numbers.
    """

    # Get Zendesk user IDs that are associated with Zendesk tickets.
    zen_user_ids = []
    for ticket in zen_tickets:
        zen_user_ids.append(ticket['requester_id'])
    zen_user_ids = set(zen_user_ids) # Remove duplicates

    # Get GitHub issue numbers that are associated with the Zendesk tickets.
    git_issue_numbers = []
    for ticket in zen_tickets:
        association_data = ''
        for field in ticket['fields']:
            if field['id'] == zen_fieldid:
                if field['value'] is not None:
                    association_data = field['value'].split('-')
                break
        if association_data and association_data[0] == 'gh':
            git_issue_numbers.append(int(association_data[1]))
    git_issue_numbers = set(git_issue_numbers) # Remove duplicates

    return (zen_user_ids, git_issue_numbers)

def get_zen_users(api_access_data, zen_user_ids):
    """Gets the full Zendesk user records for each user ID number in the passed
    list.

    Parameters:
        api_access_data - The object that contains the current user's API
                            access data necessary to access the users on their
                            Zendesk account.
        zen_user_ids - A list of Zendesk user IDs whose full user records are
                        desired.

    Returns a dictionary reference table with Zendesk user ID numbers as keys
    and their cooresponding user names as values.
    """
    # Zendesk user email set up for API token authorization
    zen_name_tk = api_access_data.zen_name + '/token'
    zen_user_reference = {} # Dictionary that allows the look up of Zendesk user
                            # names by their ID number.
    try:
        for id_number in zen_user_ids:
            request_zen_user = requests.get(
                ZEN_USER_URL % {'subdomain': api_access_data.zen_url,
                                'user_id': id_number},
                auth=(zen_name_tk, api_access_data.zen_token)
            )
            if request_zen_user.status_code != 200:
                request_zen_user.raise_for_status()
            zen_user_reference[id_number] = \
                    request_zen_user.json['user']['name']

   # Catches exceptions from requests.get() or raise_for_status()
    except RequestException as e:
        # Redefine the args attribute of the exception to contain both the
        # original error message and the name of the API responsible for causing
        # the exception.
        e.args = (e.args[0], 'Zendesk')

        # Raise the exception so it can be caught by the except in the calling
        # function for further processing.
        raise

    return zen_user_reference

def get_git_tickets(api_access_data, git_issue_numbers):
    """Gets the full GitHub ticket records for each issue number in the passed
    list.

    Parameters:
        api_access_data - The object that contains the current user's API
                            access data necessary to access the tickets on their
                            GitHub account.
        git_issue_numbers - A list of GitHub issue numbers whose full ticket
                                records are desired.

    Returns a list with a GitHub ticket record for each of the issue numbers
    passed to the function.
    """
    git_tickets = []

    try:
        for number in git_issue_numbers:
            request_git_tickets = requests.get(
                GIT_INDIVIDUAL_ISSUE_URL % \
                    {'organization': api_access_data.git_org,
                     'repository': api_access_data.git_repo,
                     'issue_number': number},
                params={'access_token': api_access_data.git_token}
            )
            if request_git_tickets.status_code != 200:
                request_git_tickets.raise_for_status()
            git_tickets.append(request_git_tickets.json)

    # Catches exceptions from requests.get() or raise_for_status()
    except RequestException as e:
        # Redefine the args attribute of the exception to contain both the
        # original error message and the name of the API responsible for causing
        # the exception.
        e.args = (e.args[0], 'GitHub')

        # Raise the exception so it can be caught by the except in the calling
        # function for further processing.
        raise

    return git_tickets

def build_enhancement_data(zen_tickets, zen_user_reference, git_tickets,
                           zen_fieldid):
    """Builds the enhancement tracking tables from the Zendesk and GitHub data.

    Parameters:
        zen_tickets - A list of open Zendesk tickets to build the enhancement
                        data from.
        zen_user_reference - A dictionary reference that can be used to look up
                                Zendesk user names by their ID number.
        git_tickets - A list of GitHub tickets that cooresponds with the
                        associated GitHub issue numbers of the Zendesk tickets
                        in zen_tics.
        zen_fieldid - The ID number of the custom field that holds the ticket
                        association value for a given Zendesk ticket.
        utc_offset - The UTC offset for the current user's time zone. Used to
                        format the date and time values for each ticket to the
                        current user's time zone.

    Returns a dictionary of the built data with the following keys and values:
        'tracking' - List of enhancements in the process of being worked on.
        'need_attention' - List of enhancements where one half of the
                            enhancement is completed, but the other is not.
        'unassociated_enhancements' - List of Zendesk tickets requesting an
                                        enhancement that have no associated
                                        external ticket.
        'not_git_enhancements' - List of Zendesk tickets that have an associated
                                    external ticket, but the ticket is not
                                    labeled as being part of GitHub. (i.e. The
                                    association string is not in the format
                                    "gh-###").
    """
    tracking = [] # Enhancements whose Zendesk and GitHub tickets are both open.
    need_attention = [] # Enhancements with either a closed Zendesk ticket or
                        # a closed GitHub ticket. Because one of these tickets
                        # is closed, the other needs attention.
    unassociated_enhancements = [] # Requested enhancements from Zendesk
                                   # tickets that have no associated external
                                   # ticket assigned to them.
    not_git_enhancements = [] # Requested enhancements from Zendesk that have an
                              # associated external ticket, but the ticket is
                              # not labeled as being part of GitHub.

    # Iterate through the Zendesk tickets using their data to classify them
    # as being tracked, needing attention, broken, or not being tracked.
    for ticket in zen_tickets:

        # Add Zendesk data to enhancement data object
        association_data = ''
        for field in ticket['fields']:
            if field['id'] == zen_fieldid:
                association_data = field['value']
                break
        if association_data:
            split_association_data = association_data.split('-')

        enhancement_data = {'zen_id': ticket['id']} # Enhancement data object
        enhancement_data = _update_enhancement_zen_data(enhancement_data,
                                                        ticket,
                                                        zen_user_reference)

        # Check if the enhancement has no associated ticket
        if not association_data:
            unassociated_enhancements.append(enhancement_data)

        # Check if the enhancement's associated ticket is not a GitHub ticket
        elif len(split_association_data) != 2 or \
                split_association_data[0] != 'gh' or \
                not split_association_data[1].isdigit():
            enhancement_data['non_git_association'] = association_data
            not_git_enhancements.append(enhancement_data)

        # Add GitHub data to the enhancement data object
        else:
            for issue in git_tickets:
                if issue['number'] == int(split_association_data[1]):
                    git_ticket = issue
                    break
            enhancement_data['git_id'] = git_ticket['number']
            enhancement_data = _update_enhancement_git_data(enhancement_data,
                                                            git_ticket)

            # Check if the enhacement should be tracked (Both tickets are
            # open).
            if enhancement_data['git_status'] == 'open':
                tracking.append(enhancement_data)

            # Check if the enhancement is in need of attention (The GitHub
            # ticket is closed).
            else:
                need_attention.append(enhancement_data)

    built_data = {
        'tracking': tracking,
        'need_attention': need_attention,
        'unassociated_enhancements': unassociated_enhancements,
        'not_git_enhancements': not_git_enhancements,
    }

    return built_data

def update_cache_index(api_access_data):
    """Updates the cache index for the passed API access model with data
    necessary for the application.

    Parameters:
        api_access_data - The object that contains the necessary access
                            parameters for getting the data needed for the
                            application from the Zendesk and GitHub APIs.

    This function will raise any RequestExceptions that happen while trying to
    access either the Zendesk or GitHub APIs so they can be properly handled by
    the calling view function.
    """
    cache_data = cache.get(api_access_data.id)

    # If the cache data isn't in the cache, build it
    if cache_data is None:
        build_cache_index(api_access_data)

    # The cache data is in the cache, so update it
    else:
        updated_zen_tickets = [] # A list of Zendesk tickets that have been
                                 # updated since the last time the cache was
                                 # updated.
        updated_git_tickets = [] # A list of GitHub tickets that have been
                                 # updated since the last time the cache was
                                 # updated.
        new_git_tickets = [] # GitHub tickets that were not previously tracked
                             # in the cache that have been newly associated with
                             # a Zendesk ticket since the last cache update.
        zen_user_ids = [] # A list of the user IDs for the requesters of the
                          # Zendesk tickets in the updated_zen_tickets list.
        git_issue_numbers = [] # A list of the issue numbers for the GitHub
                               # tickets that are associated with the Zendesk
                               # tickets in the updated_zen_tickets list.

        last_updated = cache_data['last_updated']
        zen_fieldid = api_access_data.zen_fieldid

        try:
            updated_zen_tickets = get_zen_ticket_update(api_access_data,
                                                        last_updated)
            updated_git_tickets = get_git_ticket_update(api_access_data,
                                                        last_updated)
            new_user_ids, new_issue_numbers = get_id_lists(updated_zen_tickets,
                                                           zen_fieldid)

            # Update the Zendesk user reference
            for user_id in list(new_user_ids):
                if user_id in cache_data['zen_user_reference']:
                    new_user_ids.remove(user_id)
            if new_user_ids:
                new_user_reference = get_zen_users(api_access_data,
                                                   new_user_ids)
                cache_data['zen_user_reference'] = dict(
                    cache_data['zen_user_reference'].items() + \
                    new_user_reference.items()
                )

            # Remove any GitHub tickets with no associations on Zendesk
            for ticket in list(updated_git_tickets):
                if ticket['number'] not in cache_data['git_issue_numbers']:
                    if ticket['number'] in new_issue_numbers:
                        new_git_tickets.append(ticket)
                        new_issue_numbers.remove(ticket['number'])
                    else:
                        updated_git_tickets = _rm_from_diclist(
                            updated_git_tickets, 'number', ticket['number']
                        )
                else:
                    for i in range(len(cache_data['git_tickets'])):
                        if cache_data['git_tickets'][i]['number'] == \
                        ticket['number']:
                            cache_data['git_ticket'][i] = ticket

            # Get any GitHub tickets with new Zendesk associations
            for issue_num in list(new_issue_numbers):
                if issue_num in cache_data['git_issue_numbers']:
                    new_issue_numbers.remove(issue_num)
            if new_issue_numbers:
                new_git_tickets.extend(get_git_tickets(api_access_data,
                                                       new_issue_numbers))
                cache_data['git_issue_numbers'].extend(new_issue_numbers)
                cache_data['git_tickets'].extend(new_git_tickets)

        except RequestException as e:
            # Raise RequestExceptions so they can be properly handled by
            # whatever view function call the build_cache_index function.
            raise

        # Update the cache with the updated GitHub data
        cache_data = update_git_cache(cache_data, updated_git_tickets)


        # Update the cache with the updated Zendesk data
        cache_data = update_zen_cache(cache_data, updated_zen_tickets,
                                      zen_fieldid)

        # Subtract 10 minutes from the actual time to ensure that no updates are
        # left out if they were made during the time the function was processing.
        cache_data['last_updated'] = datetime.utcnow() - timedelta(minutes=10)
        cache.set(api_access_data.id, cache_data)

def get_zen_ticket_update(api_access_data, last_updated):
    """Gets all of the Zendesk tickets that have been updated since last_updated
    for the API access data passed to the funtion.

    Parameters:
        api_access_data - The API access data that will be used to access the
                            Zendesk API in order to gather the Zendesk tickets.
        last_updated - The Zendesk tickets gathered by this function will be the
                        ones updated since this datetime.

    Returns a list of the gathered Zendesk tickets that have been updated since
    last_updated.
    """
    # Zendesk user email set up for API token authorization
    zen_name_tk = api_access_data.zen_name + '/token'
    updated_str = datetime.strftime(last_updated, '%Y-%m-%d')
    zen_tickets = []
    page = 1

    try:
        while True:
            request_zen_tickets = requests.get(
                ZEN_SEARCH_URL % {'subdomain': api_access_data.zen_url},
                params={'query': ZEN_TICKET_UPDATE_SEARCH_QUERY % \
                            {'updated': updated_str},
                        'per_page': 100,
                        'page': page},
                auth=(zen_name_tk, api_access_data.zen_token))
            if request_zen_tickets.status_code != 200:
                request_zen_tickets.raise_for_status()
            zen_tickets.extend(request_zen_tickets.json['results'])
            if request_zen_tickets.json['next_page'] is not None:
                page += 1
            else:
                break

    # Catches exceptions from requests.get() or raise_for_status()
    except RequestException as e:
        # Redefines the args attribute of the exception to contain both the
        # original error message and the name of the API responsible for causing
        # the exception.
        e.args = (e.args[0], 'Zendesk')

        # Raise the exception so it can be caught by the except in the home
        # function for further processing.
        raise

    return zen_tickets

def get_git_ticket_update(api_access_data, last_updated):
    """Gets all of the GitHub tickets that have been updated since last_updated
    for the API access data passed to the funtion.

    Parameters:
        api_access_data - The API access data that will be used to access the
                            GitHub API in order to gather the GitHub tickets.
        last_updated - The GitHub tickets gathered by this function will be the
                        ones updated since this datetime.

    Returns a list of the gathered GitHub tickets that have been updated since
    last_updated.
    """
    git_tickets = []
    updated_str = datetime.strftime(last_updated, '%Y-%m-%dT%H:%M:%SZ')
    page = 1

    try:
        while True:
            request_open_git_tickets = requests.get(
                GIT_ISSUE_URL % \
                    {'organization': api_access_data.git_org,
                     'repository': api_access_data.git_repo},
                params={'access_token': api_access_data.git_token,
                        'since': updated_str,
                        'state': 'open',
                        'sort': 'updated',
                        'per_page': 100,
                        'page': page}
            )
            if request_open_git_tickets.status_code != 200:
                request_open_git_tickets.raise_for_status()
            git_tickets.extend(request_open_git_tickets.json)
            if len(request_open_git_tickets.json) == 100:
                page += 1
            else:
                break

        while True:
            request_closed_git_tickets = requests.get(
                GIT_ISSUE_URL % \
                    {'organization': api_access_data.git_org,
                     'repository': api_access_data.git_repo},
                params={'access_token': api_access_data.git_token,
                        'since': updated_str,
                        'state': 'closed',
                        'sort': 'updated',
                        'per_page': 100,
                        'page': page}
            )
            if request_closed_git_tickets.status_code != 200:
                request_closed_git_tickets.raise_for_status()
            git_tickets.extend(request_closed_git_tickets.json)
            if len(request_closed_git_tickets.json) == 100:
                page += 1
            else:
                break

    # Catches exceptions from requests.get() or raise_for_status()
    except RequestException as e:
        # Redefine the args attribute of the exception to contain both the
        # original error message and the name of the API responsible for causing
        # the exception.
        e.args = (e.args[0], 'GitHub')

        # Raise the exception so it can be caught by the except in the calling
        # function for further processing.
        raise

    return git_tickets

def _rm_from_diclist(diclist, key_to_check, value_to_check):
    """Function that removes an entry form a list of dictionaries if a key of
    an entry matches a given value. If no value of the key_to_check matches the
    value_to_check for all of the entries in the diclist, the same diclist will
    be returned that was passed to the function.

    Parameters:
        diclist - A list of dictionaries.
        key_to_check - A key of a dictionary whose value should be checked
                        to determine if a dictionary should be removed from
                        the diclist.
        value_to_check - The value that should be compared to the value of the
                            key_to_check to determine if a dictionary should be
                            removed from the diclist.

    Returns the diclist passed to the function with an entry removed if its
    value of the key_to_check matched the value_to_check.
    """
    for i in range(len(diclist)):
        if diclist[i][key_to_check] == value_to_check:
            diclist.pop(i)
            break

    return diclist

def update_git_cache(cache_data, updated_git_tickets):
    """Updates the passed cache data with the data from the passed updated GitHub
    tickets.

    Parameters:
        cache_data - A dictionary of the cache data pulled from a group index in
                        the application's cache.
        updated_git_tickets - A list of GitHub tickets that have been updated
                                since the last update of the cache index for the
                                passed cache_data.

    Returns the cache_data object passed to the function updated with ticket
    data from the passed list of updated GitHub tickets.
    """
    for ticket in updated_git_tickets:
        ticket_found = False

        for enhancement in cache_data['tracking']:
            if enhancement['git_id'] == ticket['number']:
                enhancement = _update_enhancement_git_data(enhancement, ticket)

                if ticket['state'] == 'closed':
                    cache_data['need_attention'].append(enhancement)
                    cache_data['tracking'] = _rm_from_diclist(
                        cache_data['tracking'], 'zen_id',
                        enhancement['zen_id']
                    )
                ticket_found = True
                break
        if ticket_found:
            continue

        for enhancement in cache_data['need_attention']:
            if enhancement['git_id'] == ticket['number']:
                enhancement = _update_enhancement_git_data(enhancement, ticket)

                if ticket['state'] == 'open':
                    cache_data['tracking'].append(enhancement)
                    cache_data['need_attention'] = _rm_from_diclist(
                        cache_data['need_attention'], 'zen_id',
                        enhancement['zen_id']
                    )
                break

    return cache_data

def _update_enhancement_git_data(enhancement, git_ticket):
    """Updates the base GitHub information for an enhancement with the data from
    the passed GitHub ticket.

    Parameters:
        enhancement - A dictionary of enhancement data.
        git_ticket - A dictionary of ticket data for a GitHub ticket that will
                        be used to update the passed enhancement dictionary.

    Returns the enhancement dictionary with it's base GitHub fields updated with
    the data from the passed GitHub ticket.
    """
    enhancement['git_url'] = git_ticket['html_url']
    enhancement['git_status'] = git_ticket['state']
    git_datetime = datetime.strptime(
        git_ticket['updated_at'], "%Y-%m-%dT%H:%M:%SZ"
    )
    enhancement['git_datetime'] = git_datetime

    return enhancement

def update_zen_cache(cache_data, updated_zen_tickets, zen_fieldid):
    """Updates the passed cache data with the data from the passed updated
    Zendesk tickets.

    Parameters:
        cache_data - A dictionary of the cache data pulled from a group index in
                        the application's cache.
        updated_git_tickets - A list of Zendesk tickets that have been updated
                                since the last update of the cache index for the
                                passed cache_data.
        zen_fieldid - The ID number of the field on Zendesk tickets that holds
                        the string value of the ticket's external association.


    Returns the cache_data object passed to the function updated with ticket
    data from the passed list of updated Zendesk tickets.
    """
    not_on_gitzen = [] # A list of the Zendesk tickets in updated_zen_tickets
                       # that were not in the cache.

    for ticket in updated_zen_tickets:
        # Will be changed to True if the ticket is found in the
        # enhancement data in the cache. If it stays False, it means the
        # ticket has not had an enhancement object created for it yet.
        on_gitzen = False

        # If the ticket has been closed, it's enhancement can be removed
        # from the cache data entirely.
        if ticket['status'] == 'closed':
            cache_data['need_attention'] = _rm_from_diclist(
                cache_data['need_attention'], 'zen_id', ticket['id']
            )
            cache_data['tracking'] = _rm_from_diclist(
                cache_data['tracking'], 'zen_id', ticket['id']
            )
            cache_data['unassociated_enhancements'] = _rm_from_diclist(
                cache_data['unassociated_enhancements'], 'zen_id', ticket['id']
            )
            cache_data['not_git_enhancements'] = _rm_from_diclist(
                cache_data['not_git_enhancements'], 'zen_id', ticket['id']
            )

        else:
            association_data = ''
            for field in ticket['fields']:
                if field['id'] == zen_fieldid:
                    association_data = field['value']
                    break

            if not association_data:
                cache_data, on_gitzen = _update_zen_no_association(cache_data,
                                                                   ticket)

            else:
                cache_data, on_gitzen = _update_zen_need_attention(cache_data,
                                                        ticket, association_data)
                if on_gitzen:
                    continue
                cache_data, on_gitzen = _update_zen_tracking(cache_data, ticket,
                                                             association_data)
                if on_gitzen:
                    continue
                cache_data, on_gitzen = _update_zen_unassociated(cache_data,
                                                        ticket, association_data)
                if on_gitzen:
                    continue
                cache_data, on_gitzen = _update_zen_not_git(cache_data, ticket,
                                                            association_data)

        # Check if the ticket is a new Zendesk ticket not being tracked by
        # GitZen.
        if not on_gitzen:
            not_on_gitzen.append(ticket)

    new_enhancements = build_enhancement_data(not_on_gitzen,
                                              cache_data['zen_user_reference'],
                                              cache_data['git_tickets'],
                                              zen_fieldid)
    cache_data['need_attention'].extend(new_enhancements['need_attention'])
    cache_data['tracking'].extend(new_enhancements['tracking'])
    cache_data['unassociated_enhancements'].\
            extend(new_enhancements['unassociated_enhancements'])
    cache_data['not_git_enhancements'].\
            extend(new_enhancements['not_git_enhancements'])

    return cache_data

def _update_enhancement_zen_data(enhancement, zen_ticket, zen_user_reference):
    """Updates the base Zendesk information for an enhancement with the data from
    the passed Zendesk ticket.

    Parameters:
        enhancement - A dictionary of enhancement data.
        zen_ticket - A dictionary of ticket data for a Zendesk ticket that will
                        be used to update the passed enhancement dictionary.
        zen_user_reference - A dictionary reference for Zendesk usernames
                                with the keys being the users' IDs.

    Returns the enhancement dictionary with it's base Zendesk fields updated with
    the data from the passed Zendesk ticket.
    """
    enhancement['zen_subject'] = zen_ticket['subject']
    enhancement['zen_requester'] = zen_user_reference[zen_ticket['requester_id']]

    zen_subdomain = zen_ticket['url'].split('//')[1].split('.')[0]
    enhancement['zen_url'] = 'http://%s.zendesk.com/tickets/%s' % \
            (zen_subdomain, zen_ticket['id'])

    zen_datetime = datetime.strptime(
        zen_ticket['updated_at'], "%Y-%m-%dT%H:%M:%SZ"
    )
    enhancement['zen_datetime'] = zen_datetime

    return enhancement

def _update_zen_no_association(cache_data, zen_ticket):
    """Updates the passed cache data with the data from the passed Zendesk
    ticket which has no external ticket association.

    Parameters:
        cache_data - A dictionary of the cache data pulled from a group index in
                        the application's cache.
        zen_ticket - A dictionary with the data for a Zendesk ticket that has no
                        external ticket association.

    Returns a tuple with both the passed cache_data object updated with the data
    from the passed Zendesk ticket and a boolean that is True if the passed
    zen_ticket was found in the cache and False if the ticket was not found in
    the cache.
    """
    zen_user_reference = cache_data['zen_user_reference']

    for enhancement in cache_data['need_attention']:
        if enhancement['zen_id'] == zen_ticket['id']:
            enhancement = _update_enhancement_zen_data(enhancement, zen_ticket,
                                                       zen_user_reference)

            enhancement = _delete_enhancement_git_data(enhancement)
            cache_data['unassociated_enhancements'].append(enhancement)
            cache_data['need_attention'] = _rm_from_diclist(
                cache_data['need_attention'], 'zen_id', enhancement['zen_id']
            )
            return (cache_data, True)

    for enhancement in cache_data['tracking']:
        if enhancement['zen_id'] == zen_ticket['id']:
            enhancement = _update_enhancement_zen_data(enhancement, zen_ticket,
                                                       zen_user_reference)

            enhancement = _delete_enhancement_git_data(enhancement)
            cache_data['unassociated_enhancements'].append(enhancement)
            cache_data['tracking'] = _rm_from_diclist(
                cache_data['tracking'], 'zen_id', enhancement['zen_id']
            )
            return (cache_data, True)

    for enhancement in cache_data['unassociated_enhancements']:
        if enhancement['zen_id'] == zen_ticket['id']:
            enahancement = _update_enhancement_zen_data(enhancement, zen_ticket,
                                                        zen_user_reference)
            return (cache_data, True)

    for enhancement in cache_data['not_git_enhancements']:
        if enhancement['zen_id'] == zen_ticket['id']:
            enhancement = _update_enhancement_zen_data(enhancement, zen_ticket,
                                                       zen_user_reference)

            del enhancement['non_git_association']
            cache_data['unassociated_enhancements'].append(enhancement)
            cache_data['not_git_enhancements'] =  _rm_from_diclist(
                cache_data['not_git_enhancements'], 'zen_id',
                enhancement['zen_id']
            )
            return (cache_data, True)

    return (cache_data, False)

def _delete_enhancement_git_data(enhancement):
    """Deletes the base GitHub data fields form an enhancement dictionary.

    Parameters:
        enhancement - The enhancement dictionary from which the GitHub data
                        fields should be deleted. This dictionary must contain
                        the base GitHub fields.

    Returns the passed enhancement dictionary with all of base GitHub fields
    deleted from it.
    """
    del enhancement['git_id']
    del enhancement['git_url']
    del enhancement['git_status']
    del enhancement['git_datetime']

    return enhancement

def _update_zen_need_attention(cache_data, zen_ticket, association_data):
    """Updates the passed cache data with the data from the passed Zendesk
    ticket if the ticket is in the need_attention table.

    Parameters:
        cache_data - A dictionary of the cache data pulled from a group index in
                        the application's cache.
        zen_ticket - A dictionary with the data for a Zendesk ticket.

    Returns a tuple with both the passed cache_data object updated with the data
    from the passed Zendesk ticket and a boolean that is True if the passed
    zen_ticket was found in the need_attention table and False if the ticket was
    not found in the need_attention table.
    """
    zen_user_reference = cache_data['zen_user_reference']
    split_association_data = association_data.split('-')

    for enhancement in cache_data['need_attention']:
        if enhancement['zen_id'] == zen_ticket['id']:
            enahancemet = _update_enhancement_zen_data(enhancement, zen_ticket,
                                                       zen_user_reference)

            # If the external ticket association is no longer a regular GitHub
            # associaion, move the enhancement to the not_git_enhancements list.
            if len(split_association_data) != 2 or \
            split_association_data[0] != 'gh' or \
            not split_association_data[1].isdigit():
                enhancement = _delete_enhancement_git_data(enhancement)
                enhancement['non_git_association'] = association_data
                cache_data['not_git_enhancements'].append(enhancement)
                cache_data['need_attention'] = _rm_from_diclist(
                    cache_data['need_attention'], 'zen_id', enhancement['zen_id']
                )

            # Check if the enhancement's GitHub association has changed.
            if enhancement['git_id'] != int(split_association_data[1]):
                enhancement['git_id'] = int(split_association_data[1])

                for git_ticket in cache_data['git_tickets']:
                    if enhancement['git_id'] == git_ticket['number']:
                        enhancement = _update_enhancement_git_data(enhancement,
                                                                   git_ticket)

                        if git_ticket['state'] == 'open':
                            cache_data['tracking'].append(enhancement)
                            cache_data['need_attention'] = _rm_from_diclist(
                                cache_data['need_attention'], 'zen_id',
                                enhancement['zen_id']
                            )
                        break
            return (cache_data, True)

    return (cache_data, False)

def _update_zen_tracking(cache_data, zen_ticket, association_data):
    """Updates the passed cache data with the data from the passed Zendesk
    ticket if the ticket is in the tracking table.

    Parameters:
        cache_data - A dictionary of the cache data pulled from a group index in
                        the application's cache.
        zen_ticket - A dictionary with the data for a Zendesk ticket.

    Returns a tuple with both the passed cache_data object updated with the data
    from the passed Zendesk ticket and a boolean that is True if the passed
    zen_ticket was found in the tracking table and False if the ticket was not
    found in the tracking table.
    """
    zen_user_reference = cache_data['zen_user_reference']
    split_association_data = association_data.split('-')

    for enhancement in cache_data['tracking']:
        if enhancement['zen_id'] == zen_ticket['id']:
            enahancemet = _update_enhancement_zen_data(enhancement, zen_ticket,
                                                       zen_user_reference)

            # If the external ticket association is no longer a regular GitHub
            # associaion, move the enhancement to the not_git_enhancements list.
            if len(split_association_data) != 2 or \
            split_association_data[0] != 'gh' or \
            not split_association_data[1].isdigit():
                enhancement = _delete_enhancement_git_data(enhancement)
                enhancement['non_git_association'] = association_data
                cache_data['not_git_enhancements'].append(enhancement)
                cache_data['tracking'] = _rm_from_diclist(
                    cache_data['tracking'], 'zen_id', enhancement['zen_id']
                )

            # Check if the enhancement's GitHub association has changed.
            if enhancement['git_id'] != int(split_association_data[1]):
                enhancement['git_id'] = int(split_association_data[1])

                for git_ticket in cache_data['git_tickets']:
                    if enhancement['git_id'] == git_ticket['number']:
                        enhancement = _update_enhancement_git_data(enhancement,
                                                                   git_ticket)

                        if git_ticket['state'] == 'closed':
                            cache_data['need_attention'].append(enhancement)
                            cache_data['tracking'] = _rm_from_diclist(
                                cache_data['tracking'], 'zen_id',
                                enhancement['zen_id']
                            )
                        break
            return (cache_data, True)

    return (cache_data, False)

def _update_zen_unassociated(cache_data, zen_ticket, association_data):
    """Updates the passed cache data with the data from the passed Zendesk
    ticket if the ticket is in the unassociated_enhancements table.

    Parameters:
        cache_data - A dictionary of the cache data pulled from a group index in
                        the application's cache.
        zen_ticket - A dictionary with the data for a Zendesk ticket.

    Returns a tuple with both the passed cache_data object updated with the data
    from the passed Zendesk ticket and a boolean that is True if the passed
    zen_ticket was found in the unassociated_enhancements table and False if the
    ticket was not found in the unassociated_enhancements table.
    """
    zen_user_reference = cache_data['zen_user_reference']
    split_association_data = association_data.split('-')

    for enhancement in cache_data['unassociated_enhancements']:
        if enhancement['zen_id'] == zen_ticket['id']:
            enhancement = _update_enhancement_zen_data(enhancement, zen_ticket,
                                                       zen_user_reference)

            # If the external ticket association is not a regular GitHub
            # association, move the enhancement to the not_git_enhancements
            # list.
            if len(split_association_data) != 2 or \
            split_association_data[0] != 'gh' or \
            not split_association_data[1].isdigit():
                enhancement['non_git_association'] = association_data
                cache_data['not_git_enhancements'].append(enhancement)

            # Add the data for the enhancement's new GitHub association.
            else:
                enhancement['git_id'] = int(split_association_data[1])

                for git_ticket in cache_data['git_tickets']:
                    if enhancement['git_id'] == git_ticket['number']:
                        enhancement = _update_enhancement_git_data(enhancement,
                                                                   git_ticket)

                        if git_ticket['state'] == 'closed':
                            cache_data['need_attention'].append(enhancement)
                        else:
                            cache_data['tracking'].append(enhancement)
                        break
            cache_data['unassociated_enhancements'] = _rm_from_diclist(
                    cache_data['unassociated_enhancements'], 'zen_id',
                    enhancement['zen_id']
            )
            return (cache_data, True)

    return (cache_data, False)

def _update_zen_not_git(cache_data, zen_ticket, association_data):
    """Updates the passed cache data with the data from the passed Zendesk
    ticket if the ticket is in the not_git_enhancements table.

    Parameters:
        cache_data - A dictionary of the cache data pulled from a group index in
                        the application's cache.
        zen_ticket - A dictionary with the data for a Zendesk ticket.

    Returns a tuple with both the passed cache_data object updated with the data
    from the passed Zendesk ticket and a boolean that is True if the passed
    zen_ticket was found in the not_git_enhancements table and False if the
    ticket was not found in the not_git_enhancements table.
    """
    zen_user_reference = cache_data['zen_user_reference']
    split_association_data = association_data.split('-')

    for enhancement in cache_data['not_git_enhancements']:
        if enhancement['zen_id'] == zen_ticket['id']:
            enhancement = _update_enhancement_zen_data(enhancement, zen_ticket,
                                                       zen_user_reference)

            # Check if the external ticket association has changed.
            if enhancement['non_git_association'] != association_data:
                if len(split_association_data) != 2 or \
                split_association_data[0] != 'gh' or \
                not split_association_data[1].isdigit():
                    enhancement['non_git_association'] = asscoiation_data

                else:
                    enhancement['git_id'] = int(split_association_data[1])
                    del enhancement['non_git_association']

                    for git_ticket in cache_data['git_tickets']:
                        if enhancement['git_id'] == git_ticket['number']:
                            enhancement = \
                                _update_enhancement_git_data(enhancement,
                                                             git_ticket)

                            if git_ticket['state'] == 'closed':
                                cache_data['need_attention'].append(enhancement)
                            else:
                                cache_data['tracking'].append(enhancement)
                            cache_data['not_git_enhancements'] = \
                                _rm_from_diclist(
                                    cache_data['not_git_enhancements'], 'zen_id',
                                    enhancement['zen_id']
                                )
                            break
            return (cache_data, True)

    return (cache_data, False)
