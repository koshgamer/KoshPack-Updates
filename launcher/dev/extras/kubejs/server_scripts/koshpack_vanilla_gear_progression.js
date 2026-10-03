// Meridian / KoshPack vanilla equipment progression gate.
//
// Design rule:
// - Wood and stone gear stay early-game, but must be made through Silent Gear
//   blueprints on a normal crafting table.
// - Castable metals/gems/alloys must go through Productive Metalworks / SGear
//   Metalworks casting.
// - Vanilla weapons, tools and armor must not bypass either route.
// - Silent Gear conversion recipes are disabled so a vanilla tool obtained from
//   loot/commands/etc. cannot be converted into Silent Gear gear without the
//   intended blueprint/casting process.

var KoshVanillaGearPolicy = Java.loadClass('ru.koshpack.forgeui.server.VanillaGearPolicy')
var KOSH_VANILLA_TIERED_GEAR = []
var koshBlockedGearIterator = KoshVanillaGearPolicy.blockedIds().iterator()
while (koshBlockedGearIterator.hasNext()) {
  KOSH_VANILLA_TIERED_GEAR.push(String(koshBlockedGearIterator.next()))
}

ServerEvents.recipes(function(event) {
  // The same resource drives recipes, the viewer and server acquisition guards.
  // Using output removal covers vanilla recipe ID changes and smithing upgrades.
  KOSH_VANILLA_TIERED_GEAR.forEach(function(itemId) {
    event.remove({ output: itemId })
  })

  // Silent Gear includes convenience conversion recipes such as:
  // vanilla stone pickaxe -> Silent Gear stone pickaxe.
  // Those skip the blueprint requirement, so Meridian disables the recipe type.
  event.remove({ type: 'silentgear:conversion' })

  // Silent Gear's original blueprint needs the now-forbidden vanilla trident.
  // Keep the ocean exploration gate without depending on removed equipment.
  event.shaped('silentgear:trident_blueprint', ['#H#', '#T#', ' # '], {
    '#': '#silentgear:blueprint_paper',
    H: 'minecraft:heart_of_the_sea',
    T: 'minecraft:prismarine_crystals'
  }).id('silentgear:trident_blueprint')

  // Meridian bootstrap: vanilla wooden tools are disabled, while Silent Gear's
  // normal template-board route needs a Stone Anvil made from cobblestone.
  // These two recipes break that circular dependency without touching the
  // normal brown templates, blue blueprints, or *_quick gear recipes.
  event.shaped('silentgear:crude_knife', [
    'F',
    'S'
  ], {
    F: 'minecraft:flint',
    S: 'minecraft:stick'
  }).id('kubejs:primitive/crude_knife_flint')

  // One crude knife is intentionally spent to bootstrap exactly six boards:
  // enough for two brown pickaxe templates (wood first, stone second).
  // Once cobblestone exists, the normal Stone Anvil tool-action route takes over.
  event.shapeless(Item.of('silentgear:template_board', 6), [
    'silentgear:crude_knife',
    '#minecraft:logs'
  ]).id('kubejs:primitive/template_boards_bootstrap')
})
