from pathlib import Path

path = Path(r'C:\TikTokHistoryFactory\src\v5_factory\auto_engine.py')
code = path.read_text(encoding='utf-8')
code = code.replace('TARGET_SECONDS = 100', 'TARGET_SECONDS = 90')

# Corriger le patch d ajustement
old = '''        # Ajuster goal a la narration reelle pour eviter coupures ou silences
        total_voice = sum(voice_durations)
        if total_voice + 1 > goal:
            goal = total_voice + 1
            print(f"[DURATION] Goal adjusted to {goal}s based on voice ({total_voice}s)")'''

new = '''        # Ajuster goal a la narration reelle, borne entre 85 et 92s
        total_voice = sum(voice_durations)
        goal = min(max(total_voice + 0.5, 85.0), 92.0)
        print(f"[DURATION] Goal set to {goal:.1f}s based on voice ({total_voice:.1f}s)")'''

code = code.replace(old, new)
path.write_text(code, encoding='utf-8')
print('Done')
