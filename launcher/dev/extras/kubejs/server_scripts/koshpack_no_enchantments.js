// Project Meridian: enchantments are intentionally disabled.
// The forge treatment / sharpening system is the only item-upgrade progression.

ServerEvents.recipes(event => {
  event.remove({ id: 'minecraft:enchanting_table' })
  event.remove({ output: 'minecraft:enchanted_book' })
  event.remove({ output: 'create_enchantment_industry:blaze_enchanter' })
  event.remove({ output: 'create_enchantment_industry:classic_blaze_enchanter' })
  event.remove({ output: 'create_enchantment_industry:enchanting_template' })
  event.remove({ output: 'create_enchantment_industry:super_enchanting_template' })
  event.remove({ output: 'enchantmentlibrary:library_tier1' })
  event.remove({ output: 'enchantmentlibrary:library_tier2' })
  event.remove({ output: 'enchantmentlibrary:library_tier3' })
})
