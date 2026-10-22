# Project Meridian: Ragdoll Hits

Server-side fix for Sable: Ragdolls 0.7.5: a ragdolled player or mob is hidden and made non-attackable, so melee
hits (Better Combat swing targeting or vanilla attacks) did nothing. The mod re-runs such attacks inside the
ragdoll mod's own attack pipe (`RagdollSessionManager.RAGDOLL_PIPE_ACTIVE`), and also forwards left clicks on
ragdoll part blocks to the owner. Every forwarded hit is logged with the `[ragdoll_hits]` prefix.

Build (JDK 21, no Gradle): compile `src/` with javac against the instance `libraries/` jars plus
`sable_player_ragdoll-1.21.1-0.7.5.jar` and `sable-neoforge-1.21.1-2.0.5.jar`, then jar the classes together with
`res/META-INF/neoforge.mods.toml`.
