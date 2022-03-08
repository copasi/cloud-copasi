# condor overlay directory
This is intended to be where local condor changes to
the stock HTCondor installation source directory
(e.g. ~/condor) are kept. Here we can include any
local config additions, replacments, and patches.
The structure is meant to mimic the condor install
directory, to make it implicitly clear what might
go where, for ease of use for humans, as well as
simple Dockerfile COPY commands.
