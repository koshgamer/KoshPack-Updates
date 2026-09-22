// KoshPack Forge tooltip bridge v0.3.
//
// Professional armor still contains the old hardcoded empty-slot line in the
// DEV JAR. The real slot state is now written server-side into minecraft:lore,
// so remove only those stale placeholder lines here.

ItemEvents.modifyTooltips(event => {
  event.modifyAll(builder => {
    builder.removeText(Text.of('Заточки: [◇]'))
    builder.removeText(Text.of('Заточки: [◇] [◇]'))
    builder.removeText(Text.of('Заточки: [◇] [◇] [◇]'))
  })
})
