// KoshPack Forge Bench foundation v0.1.
// Registers the physical forge bench and the four progression consumables.

StartupEvents.registry('block', event => {
  event.create('forge_bench')
    .displayName('Кузнечный стенд')
    .hardness(5.0)
    .resistance(6.0)
    .stoneSoundType()
    .parentModel('minecraft:block/smithing_table')
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
