Implemented ``dependency_solving`` on the advanced copy endpoint. When enabled, the
copy task BFS-walks the Depends/Pre-Depends closure of every initial package, picks
the newest version satisfying each relation from the source repository, honours
Provides aliases, and skips relations already satisfied by the destination base
version. Unsatisfiable relations raise an explicit error. Resolves
:redmine:`386`.
