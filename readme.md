
# "doorman" - the garage door monitor

This project monitors my garage door and notifies me when it opens or
closes, or when it has been open late at night.

It has been through a few changes.

The first version was a two-part solution: an Arduino that was located
next to the garage door, and a Python script that ran on an internet-
connected (Linux-based) computer.  The two pieces communicate over a
bluetooth serial connection.  The Arduino board could tell whether the
door was open or closed by whether or not a magnet on the door was
close to a reed switch on the track.  The Python script ran in a loop,
asking the Arduino to look at the door every few seconds, and then
sending a message to my phone if the value changed.

More details can be found at http://blog.alanporter.com/2012-09-02/garage

I showed the project to my neighbor, and he was interested in making
one, too.  But while I had no problem running the Python script on my
always-on Linux mini-server, I did not like the idea of asking him to
leave a computer on all the time, just to watch his door.

So we came up with a second version of the project that combines the
two pieces together on a Raspberry Pi... a much more self-contained
solution.  The only things it needs are power and wifi.

This project contains:
 - the Python script that monitors the door and sends alerts
 - some startup and config files
 - code and schematics from the older Arduino+Python version
 - some pictures

## License

CC0 Public Domain - http://creativecommons.org/publicdomain/zero/1.0/

## A message from the author

This has been a very fun project, and it is useful as well.  I hope you
enjoy it.  If you have questions or comments, please contact me.

Alan Porter
(alan@alanporter.com)

