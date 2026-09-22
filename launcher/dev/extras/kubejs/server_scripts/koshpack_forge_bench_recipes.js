// KoshPack Forge Bench recipes v0.1.

ServerEvents.recipes(event => {
  event.shaped('kubejs:forge_bench', [
    'ISI',
    'BAB',
    'III'
  ], {
    I: 'minecraft:iron_ingot',
    S: 'minecraft:smithing_table',
    B: 'minecraft:blast_furnace',
    A: 'minecraft:anvil'
  }).id('kubejs:forge/bench')

  event.shapeless('4x kubejs:base_abrasive', [
    '4x minecraft:flint',
    'minecraft:sand'
  ]).id('kubejs:forge/base_abrasive')

  event.shapeless('4x kubejs:industrial_abrasive', [
    '4x minecraft:amethyst_shard',
    '2x minecraft:flint'
  ]).id('kubejs:forge/industrial_abrasive')

  event.shapeless('4x kubejs:heat_resistant_binder', [
    '2x minecraft:magma_cream',
    '2x minecraft:blaze_powder'
  ]).id('kubejs:forge/heat_resistant_binder')

  event.shapeless('4x kubejs:finishing_abrasive', [
    '2x minecraft:popped_chorus_fruit',
    '2x minecraft:amethyst_shard'
  ]).id('kubejs:forge/finishing_abrasive')
})
