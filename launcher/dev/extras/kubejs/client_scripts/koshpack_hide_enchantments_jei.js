// Project Meridian: enchantments do not exist as player progression.
// KubeJS 1.21+: RecipeViewerEvents replaces the old JEIEvents API.

RecipeViewerEvents.removeEntriesCompletely('item', event => {
  event.remove('minecraft:enchanted_book')
  event.remove('minecraft:enchanting_table')
  event.remove('minecraft:enchanted_golden_apple')
  event.remove('create_enchantment_industry:blaze_enchanter')
  event.remove('create_enchantment_industry:classic_blaze_enchanter')
  event.remove('create_enchantment_industry:enchanting_template')
  event.remove('create_enchantment_industry:super_enchanting_template')
  event.remove('enchantmentlibrary:library_tier1')
  event.remove('enchantmentlibrary:library_tier2')
  event.remove('enchantmentlibrary:library_tier3')
})
