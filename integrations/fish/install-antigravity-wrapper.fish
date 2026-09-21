# Run once with: source integrations/fish/install-antigravity-wrapper.fish
# It writes ~/.config/fish/functions/agy.fish through fish's built-in funcsave.
function agy --wraps agy --description "Antigravity CLI protected by Safer"
    command safer antigravity $argv
end
funcsave agy
echo "Safer is now guarding agy prompts. Test with: agy 'Explain this repository'"
