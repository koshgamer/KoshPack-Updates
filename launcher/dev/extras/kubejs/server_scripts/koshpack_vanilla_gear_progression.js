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

  // Do not turn vanilla salvage recipes into destructive SG salvage recipes.
  KOSH_VANILLA_TIERED_GEAR.forEach(function(itemId) {
    event.remove({ type: 'silentgear:salvaging', input: itemId })
  })
  event.remove({ id: 'farmersdelight:salvaging/leather_armor' })
  ;['gold', 'iron'].forEach(function(metal) {
    ;['smelting', 'blasting'].forEach(function(method) {
      event.remove({ id: 'minecraft:' + metal + '_nugget_from_' + method })
    })
  })

  // Create already has the copper appliance + netherite ingot upgrade route.
  ;['diving_boots', 'diving_helmet', 'backtank'].forEach(function(appliance) {
    event.remove({ id: 'create:crafting/appliances/netherite_' + appliance + '_from_netherite' })
  })

  // The SG item kind is stable; its material is stored in components.
  ;['wooden', 'stone', 'iron', 'golden', 'diamond', 'netherite'].forEach(function(tier) {
    ;['sword', 'pickaxe', 'axe', 'shovel', 'hoe'].forEach(function(kind) {
      event.replaceInput({}, 'minecraft:' + tier + '_' + kind, 'silentgear:' + kind)
    })
  })
  ;['bow', 'crossbow', 'shield', 'trident', 'mace', 'shears', 'fishing_rod'].forEach(function(kind) {
    event.replaceInput({}, 'minecraft:' + kind, 'silentgear:' + kind)
  })

  // Preserve the upgrade's material charge when any SG shovel becomes the base.
  event.shapeless('silentgear:road_maker_upgrade', [
    'silentgear:advanced_upgrade_base', 'silentgear:shovel', '#c:ingots/iron', '#c:dyes/orange'
  ]).id('silentgear:road_maker_upgrade')
  event.shapeless('silentgear:spoon_upgrade', [
    'silentgear:advanced_upgrade_base', 'silentgear:shovel', 'minecraft:diamond'
  ]).id('silentgear:spoon_upgrade')

  // Smithing has only three inputs: move these upgrades to normal assembly so
  // SG armor, one netherite ingot, the boss drop and the template all stay required.
  ;['cursium', 'ignitium'].forEach(function(material) {
    ;['boots', 'chestplate', 'helmet', 'leggings'].forEach(function(piece) {
      var id = 'cataclysm:smithing/' + material + '_' + piece
      event.remove({ id: id })
      event.shapeless('cataclysm:' + material + '_' + piece, [
        'silentgear:' + piece, 'minecraft:netherite_ingot',
        'cataclysm:' + material + '_ingot', 'cataclysm:' + material + '_upgrade_smithing_template'
      ]).id(id)
    })
  })
  event.remove({ id: 'cataclysm:smithing/monstrous_helm' })
  event.shapeless('cataclysm:monstrous_helm', [
    'silentgear:helmet', 'minecraft:netherite_ingot', 'cataclysm:monstrous_horn',
    'minecraft:netherite_upgrade_smithing_template'
  ]).id('cataclysm:smithing/monstrous_helm')
  event.remove({ id: 'cataclysm:the_incinerator' })
  event.shapeless('cataclysm:the_incinerator', [
    'silentgear:sword', 'minecraft:netherite_ingot',
    'cataclysm:ignitium_ingot', 'cataclysm:ignitium_ingot',
    'minecraft:blaze_rod', 'minecraft:blaze_rod', 'minecraft:blaze_rod', 'minecraft:blaze_rod'
  ]).id('cataclysm:the_incinerator')

  // Semji's JSON is only a JEI preview; its workbench checks vanilla items in
  // Java. Add two real assembly routes instead of publishing misleading previews.
  event.remove({ id: 'semji_clothing:exilearmor_jei' })
  event.remove({ id: 'semji_clothing:twometerderby_jei' })
  event.shapeless('semji_clothing:exile_armor_chestplate', [
    'minecraft:netherite_ingot', 'minecraft:lava_bucket', 'semji_clothing:special_suit_template',
    'minecraft:ender_eye', 'silentgear:chestplate', 'minecraft:diamond_block'
  ]).id('kubejs:progression/semji_exile_armor')
  event.shapeless('semji_clothing:two_meter_derby_boots', [
    'minecraft:netherite_ingot', 'minecraft:lava_bucket', 'semji_clothing:special_suit_template',
    'minecraft:ender_eye', 'silentgear:boots',
    'minecraft:leather', 'minecraft:leather', 'minecraft:leather', 'minecraft:leather'
  ]).id('kubejs:progression/semji_derby_boots')

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
