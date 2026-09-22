// KoshPack Forge Bench foundation v0.1.
// Registers the physical forge bench and the four progression consumables.

StartupEvents.registry('block', event => {
  event.create('forge_bench')
    .displayName('Кузнечный стенд')
    .hardness(5.0)
    .resistance(6.0)
    .stoneSoundType()
    .modelGenerator(m => {
      // Keep the custom collision boxes below, but render the authored model as-is.
      // Using parentModel together with .box() makes KubeJS generate child elements
      // that reference undefined #north/#south/#up textures -> magenta/black model.
      m.parent('koshpack_forge_ui:block/forge_bench')
    })
    .box(1, 0, 1, 15, 10, 15)
    .box(0, 10, 0, 16, 14, 16)
    .box(3, 14, 4, 13, 16, 12)
})

StartupEvents.registry('item', event => {
  event.create('base_abrasive')
    .displayName('Базовый абразив')
    .maxStackSize(64)
    .texture('minecraft:item/flint')

  event.create('industrial_abrasive')
    .displayName('Промышленный абразив')
    .maxStackSize(64)
    .texture('minecraft:item/amethyst_shard')

  event.create('heat_resistant_binder')
    .displayName('Жаростойкая связка')
    .maxStackSize(64)
    .texture('minecraft:item/magma_cream')

  event.create('finishing_abrasive')
    .displayName('Финишный абразив')
    .maxStackSize(64)
    .texture('minecraft:item/echo_shard')
})
