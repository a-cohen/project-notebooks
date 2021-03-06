__author__ = "Jeremy Nelson"
__license__ = "Apache 2"
"""documentation for https://developer.github.com/v4/"""

import datetime
import data
import os
import pandas as pd
import requests

GITHUB_URL = 'https://api.github.com/graphql'
ROOT_DIR = os.path.abspath(".").split('/Sinopia')[0]
ENV_PATH = os.path.join(ROOT_DIR, '.env')
with open(ENV_PATH) as fo:
    token = fo.read()[:-1]
    GITHUB_HEADERS = {'Authorization': f"token {token}"}


def all_issues(**kwargs):
    """Queries Github and retrieves all state issues in a Github repository


    Keyword arguments:
    repo -- The name of the LD4P repository (defaults sinopia_editor)
    state -- The state of the issues, (defaults OPEN)
    """
    issues = []
    repo = repo=kwargs.get('repo', 'sinopia_editor')
    closed_issues = issues_query(repo=repo,
                                 state="CLOSED")
    issues.append(closed_issues)
    hasNextPage = closed_issues['data']['repository']['issues']['pageInfo']['hasNextPage']
    while hasNextPage:
        closed_issues = issues_query(repo=repo,
            state="CLOSED",
            after=closed_issues['data']['repository']['issues']['pageInfo']['endCursor'])
        issues.append(closed_issues)
        hasNextPage = closed_issues['data']['repository']['issues']['pageInfo']['hasNextPage']
    return issues

def all_pull_requests(**kwargs):
    """Queries Github and retrieves all PRs from a Github repository

    Keyword arguments:
    repo -- The  name of the LD4P repository (defaults sinopia_editor)
    """
    pull_requests = {}
    repo = repo=kwargs.get('repo', 'sinopia_editor')
    pr_shard = pull_requests_query(repo=repo)
    pull_requests.append(pr_shard)
    hasNextPage = pr_shard['data']['repository']['pullRequests']['pageInfo']['hasNextPage']
    while hasNextPage:
        pr_shard = pull_requests_query(repo=repo,
            after=pr_shard['data']['repository']['pullRequests']['pageInfo']['endCursor'])
        pull_requests.append(pr_shard)
        hasNextPage = pr_shard['data']['repository']['pullRequests']['pageInfo']['hasNextPage']
    return pull_requests

def __get_after__(**kwargs):
    """Helper function returns string for Graph QL after"""
    after = kwargs.get('after', '')
    if len(after) > 0:
        after = """, after: "{after}" """.format(after=after)
    return after

def __pr_data_frame__(pr_shard):
    output = {}
    commits_sha = []
    pr_author = []
    pr_number = []
    pr_createdAt = []
    pr_mergedAt = []
    pr_mergedBy = []
    pr_title = []
    for row in pr_shard['data']['repository']['pullRequests']['edges']:
        node = row['node']
        pr_number.append(node['number'])
        pr_author.append(node['author']['login'])
        pr_createdAt.append(pd.Timestamp(node['createdAt']))
        pr_mergedAt.append(pd.Timestamp(node['mergedAt']))
        pr_mergedBy.append(node['mergedBy']['login'])
        pr_title.append(node['title'])
        # Needs commits __pr_series__
    ds_author = pd.Series(pr_author, index=pr_number)
    ds_createdAt = pd.Series(pr_createdAt, index=pr_number)
    ds_mergedAt = pd.Series(pr_mergedAt, index=pr_number)
    ds_title = pd.Series(pr_title, index=pr_number)
    pr_df = pd.DataFrame({
        "author": ds_author,
        "createdAt": ds_createdAt,
        "mergedAt": ds_mergedAt,
        "title": ds_title},
        index=pr_number)
    pr_df['elapsed'] = pr_df['mergedAt'] - pr_df['createdAt']
    return pr_df

def commits_query(**kwargs):
    """Queries repository for commits and returns JSON

    Keyword arguments:
    repo -- The name of the LD4P repository (defaults sinopia_editor)
    branch -- Branch (defaults to master)
    state -- The state of the issues, (defaults OPEN)
    first -- number of items from the first (defaults 100)
    after -- End cursor
    """
    after = __get_after__(**kwargs)
    query = {
        'query': """{{
            repository(owner:"LD4P", name:"{repo}") {{
              ref(qualifiedName: {branch}) {{
                target {{
                  ... on Commit {{
                     id
                     history(first: {first}, {after}) {{
                       pageInfo {{
                        startCursor
                        hasNextPage
                        endCursor
                       }}
                      edges {{
                        node {{
                          messageHeadline
                          oid
                          message
                          author {{
                            user {{
                              login
                            }}
                            date
                          }}
                        }}
                      }}
                     }}
                  }}
                }}
              }}
            }}
        }}""".format(repo=kwargs.get('repo', 'sinopia_editor'),
                     branch=kwargs.get('branch', 'master'),
                     first=kwargs.get('first', 100),
                     after=after)
    }
    result = requests.post(url=GITHUB_URL, json=query, headers=GITHUB_HEADERS)
    payload = result.json()
    if "errors" in payload.keys():
        print(payload)
    return payload

def issues_query(**kwargs):
    """Queries with graph QL for issues and returns json

    Keyword arguments:
    repo -- The name of the LD4P repository (defaults sinopia_editor)
    state -- The state of the issues, (defaults OPEN)
    first -- number of items from the first (defaults 100)
    after -- End cursor
    """
    after = __get_after__(**kwargs)
    query = {
        'query': """{{
            repository(owner:"LD4P", name:"{repo}") {{
              issues(first:{first} {after}) {{
                pageInfo {{
                    startCursor
                    hasNextPage
                    endCursor
                }}
                edges {{
                  node {{
                    title
                    url
                    number
                    createdAt
                    closedAt
                    projectCards(first:5) {{
                      edges {{
                          node {{
                              project {{
                                      name
                                      number
                              }}
                              state
                          }}
                      }}
                    }}
                    participants(first:10) {{
                        edges {{
                            node {{
                                login
                            }}
                        }}
                    }}
                    state
                  }}
                }}
              }}
           }}
        }}
    """.format(state=kwargs.get('state', 'OPEN'),
               first=kwargs.get('first', 100),
               repo=kwargs.get('repo', 'sinopia_editor'),
               after=after)
    }
    result = requests.post(url=GITHUB_URL, json=query, headers=GITHUB_HEADERS)
    payload = result.json()
    if "errors" in payload.keys():
        print(payload)
    return payload

def pull_requests_query(**kwargs):
    """Queries repository for pull requests and returns JSON

    Keyword arguments:
    repo -- The name of the LD4P repository (defaults sinopia_editor)
    first -- number of items from the first (defaults 100)
    after -- End cursor
    """
    after = __get_after__(**kwargs)
    query = {
        'query': """{{
            repository(owner:"LD4P", name:"{repo}") {{
                pullRequests(baseRefName: "master", first: {first}, {after}) {{
                    pageInfo {{
                        startCursor
                        hasNextPage
                        endCursor
                    }}
                    edges {{
                      node {{
                        author {{
                          login
                        }}
                        closedAt
                        commits(first: 100) {{
                           edges {{
                              node {{
                                  commit {{
                                    oid
                                    additions
                                    deletions
                                    committedDate
                                    messageHeadline
                                    author {{
                                        user {{
                                          login
                                        }}
                                        date
                                    }}
                                  }}
                              }}
                          }}
                        }}
                        createdAt
                        closedAt
                        mergedAt
                        mergedBy {{
                          login
                        }}
                        number
                        title
                        state
                      }}
                    }}
                }}
            }}
        }}""".format(repo=kwargs.get('repo', 'sinopia_editor'),
                     first=kwargs.get('first', 100),
                     after=after)
    }
    result = requests.post(url=GITHUB_URL, json=query, headers=GITHUB_HEADERS)
    payload = result.json()
    if "errors" in payload.keys():
        print(payload)
    return payload

def write_closed_issues(all_closed):
    """Takes a listing of all closed issues and persists JSON to filesystem

    Arguments:
    all_closed -- list of issues from all_issues functions
    """
    for i, row in enumerate(all_closed):
        i+=1
        filename = f"../data/json/issues-closed-{i:03}.json"
        if os.path.exists(filename):
            continue
        with open(filename, "w+") as fo:
            json.dump(row['data']['repository']['issues']['edges'], fo, indent=2, sort_keys=True)
