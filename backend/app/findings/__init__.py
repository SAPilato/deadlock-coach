"""Findings engine: rules scan a MatchContext and return short, ranked, fixable findings.

Add a rule: create a module in `rules/`, subclass `Rule`, decorate with `@register`,
put every user-facing string in `TEXT`, and add a test. The readability test checks
every template automatically.
"""
