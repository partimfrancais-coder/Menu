'use strict';
// Fragment tokens do not enter HTTP access logs or referrer headers.
if(location.hash) document.querySelector('#invite-token').value=location.hash.slice(1);
