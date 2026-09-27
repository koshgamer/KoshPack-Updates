// Project Meridian: enchantments do not exist as player progression.
// Hide the vanilla enchanting UI/items from JEI so the catalog matches gameplay.

JEIEvents.hideItems(event => {
  event.hide('minecraft:enchanted_book')
  event.hide('minecraft:enchanting_table')
  event.hide('minecraft:enchanted_golden_apple')
})
