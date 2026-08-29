"""Notifications: telling a person, outside the application, that something happened.

Deliberately minimal: one channel (WhatsApp, through Evolution API), one
recipient (the owner), no templates. It is the seam where the notification
problem will grow, and today it exists so an interrupted price update does not
wait for somebody to open the screen.
"""
