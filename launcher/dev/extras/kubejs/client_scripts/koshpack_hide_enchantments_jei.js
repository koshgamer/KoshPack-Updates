// Project Meridian: enchantments do not exist as player progression.
// KubeJS 1.21+: RecipeViewerEvents replaces the old JEIEvents API.

RecipeViewerEvents.removeEntriesCompletely('item', event => {
  event.remove('minecraft:enchanted_book')
  event.remove('minecraft:enchanting_table')
  event.remove('minecraft:enchanted_golden_apple')
})
