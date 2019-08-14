# Brick is a modular and expandable chat-bot capable of basic learning and information fetching by API calls.
# Copyright (C) 2015  Bill Ballou

# This file is part of Brick.

# Brick is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.

# Brick is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Brick.  If not, see <http://www.gnu.org/licenses/>.

import cmd
import brick
from util import log

name     = 'Ballou'
userid   = '7659157'

# Live
group_id = '5212503'

# Betabrick
# group_id = '9908601'

message = {
        'attachments' : [],
        'user_id'     : userid,
        'id'          : '141011428630974889',
        'created_at'  : '14114286',
        'name'        : name,
        'avatar_url'  : 'https://i.groupme.com/6fcb4e7039e901301cc21231394268a3.avatar',
        'group_id'    : group_id,
        'system'      : False,
        'text'        : ""
        }


class terminal(cmd.Cmd):
    # Input processor

    # Process Input
    def default(self, line):
        message['text'] = line
        brick.handler(message)
    
    # Exit Terminal
    def do_quit(self, line):
        return True

    # Changes terminal user
    def do_setuser(self, line):
        message['name'] = line
        log("User changed to " + repr(line))

    # Changes terminal userid
    def do_setid(self, line):
        message['user_id'] = line
        log("User ID changed to " + repr(line))

    # Changes terminal group
    def do_setgroup(self, line):
        message['group_id'] = line
        log("Group changed to " + repr(line))

    # Sends a heartbeat command
    def do_pulse(self, line):
        log("Triggering Heartbeat")
        brick.heartbeat()


# Program Loop
if __name__ == '__main__':
    try:
        terminal().cmdloop()
    except KeyboardInterrupt:
        pass