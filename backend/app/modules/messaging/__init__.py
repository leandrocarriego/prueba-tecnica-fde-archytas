"""Messaging: the inbox of the portal, brought out of the screen nobody opens.

The problem the spec states is not that the inbox is badly built — it is that
it lives inside a system nobody enters. So this module's job is to take those
messages out of there, put a state and an owner on each one, and hand the ones
that matter to `notifications`, which delivers them somewhere the team actually
looks.
"""
