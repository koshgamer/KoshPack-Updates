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

    // The DEV armor JAR still prints the old fixed-by-tier physical stats and
    // repair materials. Material-bearing Foundry plates now own those values.
    builder.removeText(Text.of('Полный комплект: 12 защиты'))
    builder.removeText(Text.of('Полный комплект: 15 защиты'))
    builder.removeText(Text.of('Полный комплект: 20 защиты • 8 стойкости'))
    builder.removeText(Text.of('Полный комплект: 20 защиты • 12 стойкости • 0.4 сопр. отбрасыванию'))
    builder.removeText(Text.of('Ремонт: железо • Обычные чары разрешены'))
    builder.removeText(Text.of('Ремонт: алмаз • Обычные чары разрешены'))
    builder.removeText(Text.of('Ремонт: незерит • Обычные чары разрешены'))
  })
})
