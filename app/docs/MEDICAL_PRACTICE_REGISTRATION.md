# Medical Practice Registration Flow

## Overview
When a request is made to register a medical practice, three things occur:
- A 'pending' user is created as a so-called master user in the `pending_users` table
- The medical practice entity is created in the database
- An email is sent to the master user so they can complete the registration process. The email contains a link to the form, with the token in the query string under the name `token`. This string is a UUID and is therefore URL safe.


## Registration Tokens
Registration tokens allow the 'one-time' style requests to the API.
They act as a token for a password to be created for the master user
initially, without them having created a password.

## Converting Users
In order to convert the pending user to a full user, the `/convert` endpoint should be called.
With this request, the password and registration token should be 
passed in the payload.