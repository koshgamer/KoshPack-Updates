// Project Meridian: enchantments are intentionally disabled.
// The forge treatment / sharpening system is the only item-upgrade progression.

ServerEvents.recipes(event => {
  event.remove({ id: 'minecraft:enchanting_table' })
  event.remove({ output: 'minecraft:enchanted_book' })
})
