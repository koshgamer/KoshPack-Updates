// KoshPack curated alloy progression v1.
//
// Goal:
// - Productive Metalworks / SGear Metalworks Foundry is the canonical alloy path.
// - Alternative mixer/crafting shortcuts are disabled.
// - Silent Gear's arbitrary Crude/Super Alloy routes are disabled so progression
//   is built from named engineering alloys instead of "mix anything" compounds.
//
// Progression:
// I   basic engineering alloys: brass / bronze / electrum / invar / steel
// II  special materials: blaze gold / crimson iron / azure silver / netherite
// III advanced alloys: crimson steel / azure electrum
// IV  tyrian steel
// V   uru metal
//
// The actual fluid alloying recipes stay owned by Productive Metalworks and
// SGear Metalworks. This script only closes bypasses; it does not duplicate
// upstream recipes and therefore cannot desync their ratios.

var KOSH_ALLOY_BYPASS_RECIPE_IDS = [
  // Create / Create add-ons: keep these alloys in the Foundry.
  'create:mixing/brass_ingot',
  'createaddition:mixing/electrum',
  'createbigcannons:mixing/bronze',
  'createbigcannons:mixing/alloy_bronze',

  // Create Metallurgy has a second alloying path. KoshPack uses Productive
  // Metalworks as the single source of truth for these common alloys.
  'createmetallurgy:alloying/brass',
  'createmetallurgy:alloying/bronze',
  'createmetallurgy:alloying/constantan',
  'createmetallurgy:alloying/electrum',
  'createmetallurgy:alloying/invar',
  'createmetallurgy:alloying/steel',
  'createmetallurgy:alloying/netherite',

  // Netherite is alloyed from molten ancient debris + gold in the Foundry.
  'minecraft:netherite_ingot'
]

var KOSH_SILENTGEAR_SPECIAL_ALLOYS = [
  'blaze_gold',
  'crimson_steel',
  'azure_electrum',
  'tyrian_steel'
]

ServerEvents.recipes(function(event) {
  KOSH_ALLOY_BYPASS_RECIPE_IDS.forEach(function(id) {
    event.remove({ id: id })
  })

  // Silent Gear also ships crafting-table / Alloy Forge routes for its named
  // alloys. Keep block/nugget recycling, but remove creation shortcuts.
  KOSH_SILENTGEAR_SPECIAL_ALLOYS.forEach(function(material) {
    event.remove({ id: 'silentgear:' + material + '_ingot' })
    event.remove({ id: 'silentgear:alloying/metal/' + material + '_ingot' })
  })

  // These machines deliberately accept arbitrary material combinations.
  // They would bypass KoshPack's named-alloy progression completely.
  event.remove({ type: 'silentgear:alloy_making_crude' })
  event.remove({ type: 'silentgear:alloy_making/super' })
  event.remove({ output: 'silentgear:crude_mixer' })
  event.remove({ output: 'silentgear:super_mixer' })

  // The standalone Silent Gear Alloy Forge duplicates the Foundry route.
  // Fresh KoshPack worlds should use the Productive Metalworks Foundry.
  event.remove({ output: 'silentgear:alloy_forge' })
})
