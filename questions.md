# Floy Technical Challenge

## Questions

**1. What were the reasons for your choice of API/protocol/architectural style used for the client-server communication?**]
- Rest API because is stateless, uses the HTTP protocal which is simple, easy to understand, use, maintain and scale. It's also easy to encrypt the data with HTTPS, which would help us keep the data secure during transmission.
- FastAPI because it is lightweight, with asynchronous code support. It is also quite easy for new devs with prior python knowledge to onboard on small codebases.
- For DB, I did consider mongoDB, but ended up choosing the traditional SQL because even tho we have only a single table, I can imagine that the extracted information within a business environment can easily be related with other information, and SQL make it easier to manage structured data. 
For the prototype I am using SQLite, for production, depending on the situation I'd go for PostgreSQL


**2.  As the client and server communicate over the internet in the real world, what measures would you take to secure the data transmission and how would you implement them?**

- Firewall can be put in place so that only the desired parties can reach each other.
- Use TLS or SSL to encrypt the communication between the client and server.
- Use Token Authentication. Tokens that expire, maybe the closest possible to the end of working hours.
- The data can also be stored in an encrypted way.
- From time to time, perform some penetration tests in order to anticipate possible vulnerabilities.

