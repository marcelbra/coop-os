"""Write iTerm2 Dynamic Profiles for coop-os.

Reads the Default profile font from iTerm2 preferences, scales it to 200% for
both panes, then writes both profiles (coop-os-tui and coop-os-agent) to the
iTerm2 DynamicProfiles directory.
"""

from coop_os.iterm_launch import write_iterm_profiles

write_iterm_profiles()
