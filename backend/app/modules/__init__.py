"""Domain modules.

Each module is self-contained: routes, schemas, service, repository, models and
tasks live together. A module talks to another module **only** through its
`service.py` — never its repository, never its models.
"""
