// Meridian / KoshPack vanilla weapon-tool progression gate.
//
// Design rule:
// - Wood and stone gear stay early-game, but must be made through Silent Gear
//   blueprints on a normal crafting table.
// - Castable metals/gems/alloys must go through Productive Metalworks / SGear
//   Metalworks casting.
// - Vanilla tiered weapon/tool recipes must not bypass either route.
// - Silent Gear conversion recipes are disabled so a vanilla tool obtained from
//   loot/commands/etc. cannot be converted into Silent Gear gear without the
//   intended blueprint/casting process.

var KOSH_VANILLA_TIERED_GEAR = [
  // Wooden
  'minecraft:wooden_sword',
  'minecraft:wooden_pickaxe',
  'minecraft:wooden_axe',
  'minecraft:wooden_shovel',
  'minecraft:wooden_hoe',

  // Stone
  'minecraft:stone_sword',
  'minecraft:stone_pickaxe',
  'minecraft:stone_axe',
  'minecraft:stone_shovel',
  'minecraft:stone_hoe',

  // Iron
  'minecraft:iron_sword',
  'minecraft:iron_pickaxe',
  'minecraft:iron_axe',
  'minecraft:iron_shovel',
  'minecraft:iron_hoe',

  // Gold
  'minecraft:golden_sword',
  'minecraft:golden_pickaxe',
  'minecraft:golden_axe',
  'minecraft:golden_shovel',
  'minecraft:golden_hoe',

  // Diamond
  'minecraft:diamond_sword',
  'minecraft:diamond_pickaxe',
  'minecraft:diamond_axe',
  'minecraft:diamond_shovel',
  'minecraft:diamond_hoe',

  // Netherite
  'minecraft:netherite_sword',
  'minecraft:netherite_pickaxe',
  'minecraft:netherite_axe',
  'minecraft:netherite_shovel',
  'minecraft:netherite_hoe'
]

ServerEvents.recipes(function(event) {
  KOSH_VANILLA_TIERED_GEAR.forEach(function(itemId) {
    event.remove({ output: itemId })
  })

  event.remove({ type: 'silentgear:conversion' })
})
