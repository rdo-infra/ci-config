# Introduction

Reviewbot adds patches which need reviews to the tripleo ci Review list.
It joins #oooq with a bot account and listens to for pattern like "Add to review list ..." or "Need review ..."

# How to run
- Install requirements
- export auth_token (from hackmd account), note_id (of the hackmd review list) 
- `./ircbot.py irc.oftc.net:6667 name_of_channel username_of_bot`

