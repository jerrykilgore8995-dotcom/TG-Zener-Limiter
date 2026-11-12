"""Apply small, source-controlled TG12413 JUCE v1.2 updates after archive extraction.
The preserved original measured DSP, meters and panel are not replaced.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] if Path(__file__).resolve().parent.name == '.build-updates' else Path(__file__).resolve().parent


def change(rel, old, new):
    path = ROOT / rel
    value = path.read_text(encoding='utf-8')
    if old not in value:
        raise RuntimeError(f'Expected anchor not found in {rel}: {old[:100]!r}')
    value = value.replace(old, new, 1)
    path.write_text(value, encoding='utf-8')

# Attack values retained in a discrete three-position control; default=stock 8 ms.
change('Source/TGFastZenerLimiter.h',
       '    int recovery=1;     // 50,100,250,500,1000,2000 ms\n',
       '    int recovery=1;     // 50,100,250,500,1000,2000 ms\n'
       '    int attackMode=1;   // Fast 1ms, Med 8ms (default), Slow 15ms\n')
change('Source/TGFastZenerLimiter.h',
       'inline constexpr std::array<double,6> recoveries{50.,100.,250.,500.,1000.,2000.};',
       'inline constexpr std::array<double,3> attacks{1.,8.,15.};\n'
       'inline constexpr std::array<double,6> recoveries{50.,100.,250.,500.,1000.,2000.};')
change('Source/TGFastZenerLimiter.h',
       'c.outputPct=std::clamp(c.outputPct,0,100); c.recovery=std::clamp(c.recovery,0,5);',
       'c.outputPct=std::clamp(c.outputPct,0,100); c.recovery=std::clamp(c.recovery,0,5);\n'
       '        c.attackMode=std::clamp(c.attackMode,0,2);')
change('Source/TGFastZenerLimiter.h',
       '        release_=std::exp(-1./(fs_*recoveries[c_.recovery]*.001));}',
       '        attack_=std::exp(-1./(fs_*attacks[c_.attackMode]*.001));\n'
       '        release_=std::exp(-1./(fs_*recoveries[c_.recovery]*.001));}')

change('Source/PluginProcessor.cpp',
       '    params.add(std::make_unique<juce::AudioParameterBool> (\n'
       '        juce::ParameterID { "softKnee", 1 }, "Soft knee", false));',
       '    params.add(std::make_unique<juce::AudioParameterChoice> (\n'
       '        juce::ParameterID { "attack", 1 }, "Attack",\n'
       '        juce::StringArray { "Fast (1 ms)", "Med (8 ms)", "Slow (15 ms)" }, 1));\n'
       '    params.add(std::make_unique<juce::AudioParameterBool> (\n'
       '        juce::ParameterID { "softKnee", 1 }, "Soft knee", false));')
change('Source/PluginProcessor.cpp',
       '    c.softKnee = parameters.getRawParameterValue("softKnee")->load() > 0.5f;',
       '    c.attackMode = juce::jlimit(0, 2, static_cast<int>(std::lround(\n'
       '                       parameters.getRawParameterValue("attack")->load())));\n'
       '    c.softKnee = parameters.getRawParameterValue("softKnee")->load() > 0.5f;')

change('Source/PluginEditor.h',
       'class TGZenerRackAudioProcessorEditor final : public juce::AudioProcessorEditor,',
       '''// Pushbutton cycles through the three attack settings (no slider dragging).
// Deriving from Slider allows ordinary JUCE APVTS parameter attachment/automation.
class TGAttackButton final : public juce::Slider
{
public:
    void mouseDown(const juce::MouseEvent&) override;
    void mouseDrag(const juce::MouseEvent&) override {}
};

class TGAttackButtonLook final : public juce::LookAndFeel_V4
{
public:
    void drawLinearSlider(juce::Graphics&, int, int, int, int,
                          float, float, float,
                          const juce::Slider::SliderStyle, juce::Slider&) override;
};

class TGZenerRackAudioProcessorEditor final : public juce::AudioProcessorEditor,''')
change('Source/PluginEditor.h',
       '    TGChickenHeadLook knobLook;\n',
       '    TGChickenHeadLook knobLook;\n    TGAttackButtonLook attackButtonLook;\n')
change('Source/PluginEditor.h',
       '    TGPanelPushButton cellButton, inButton;',
       '    TGAttackButton attackL, attackR;\n    TGPanelPushButton cellButton, inButton;')
change('Source/PluginEditor.h',
       '    std::unique_ptr<juce::AudioProcessorValueTreeState::SliderAttachment> inLAttach, outLAttach, recLAttach;',
       '    std::unique_ptr<juce::AudioProcessorValueTreeState::SliderAttachment> inLAttach, outLAttach, recLAttach, attLAttach;')
change('Source/PluginEditor.h',
       '    std::unique_ptr<juce::AudioProcessorValueTreeState::SliderAttachment> inRAttach, outRAttach, recRAttach;',
       '    std::unique_ptr<juce::AudioProcessorValueTreeState::SliderAttachment> inRAttach, outRAttach, recRAttach, attRAttach;')

button_code = r'''// This is a physical-style illuminated momentary pushbutton, not a fader.
// Each click advances 1ms -> 8ms -> 15ms -> 1ms. Both linked channels update.
void TGAttackButton::mouseDown(const juce::MouseEvent&)
{
    if (onDragStart) onDragStart();
    setValue(static_cast<double>((juce::roundToInt(getValue()) + 1) % 3),
             juce::sendNotificationSync);
    if (onDragEnd) onDragEnd();
}

void TGAttackButtonLook::drawLinearSlider(juce::Graphics& g, int x, int y, int w, int h,
                                         float, float, float,
                                         const juce::Slider::SliderStyle, juce::Slider& slider)
{
    const int selected = juce::jlimit(0, 2, juce::roundToInt(slider.getValue()));
    const juce::Colour active[] = {
        juce::Colour::fromRGB(240, 56, 41),
        juce::Colour::fromRGB(255, 171, 62),
        juce::Colour::fromRGB(87, 192, 255)
    };

    const float bx = static_cast<float>(x) + 9.0f;
    const float by = static_cast<float>(y) + 29.0f;
    const auto bezel = juce::Rectangle<float>(bx, by, 42.0f, 42.0f);
    const auto lens = bezel.reduced(5.0f);

    // Cast shadow and machined metal edge: dimensions match the THD/IN switches.
    g.setColour(juce::Colours::black.withAlpha(0.48f));
    g.fillRoundedRectangle(bezel.translated(2.0f, 2.3f), 4.0f);
    g.setColour(juce::Colour::fromRGB(18, 21, 25));
    g.fillRoundedRectangle(bezel, 4.0f);
    g.setColour(juce::Colour::fromRGB(155, 166, 171));
    g.drawRoundedRectangle(bezel, 4.0f, 1.4f);
    g.setColour(juce::Colour::fromRGB(7, 10, 12));
    g.fillRoundedRectangle(lens.expanded(1.6f), 3.0f);

    // Frosted acrylic cap, colored internal lamp and subtle reflected highlight.
    const auto c = active[selected];
    g.setColour(c.withAlpha(0.17f));
    g.fillRoundedRectangle(lens.expanded(2.7f), 4.5f);
    juce::ColourGradient body(c.brighter(0.75f), lens.getTopLeft(),
                              c.darker(0.28f), lens.getBottomRight(), false);
    body.addColour(0.4, c.brighter(0.18f));
    g.setGradientFill(body);
    g.fillRoundedRectangle(lens, 2.8f);
    g.setColour(juce::Colours::white.withAlpha(0.48f));
    g.fillRoundedRectangle(lens.withHeight(4.5f).reduced(2.0f, 0.0f), 1.5f);
    g.setColour(juce::Colours::black.withAlpha(0.34f));
    g.drawRoundedRectangle(lens, 2.8f, 1.5f);

    const juce::String labels[] = { "FAST  1ms", "MED   8ms", "SLOW 15ms" };
    const float labelX = static_cast<float>(x) + 64.0f;
    for (int i = 0; i < 3; ++i)
    {
        const float rowY = static_cast<float>(y) + 10.0f + i * 28.0f;
        const juce::Rectangle<float> region(labelX, rowY, juce::jmax(0.0f,
                        static_cast<float>(w) - 65.0f), 24.0f);
        const bool lit = (i == selected);
        g.setFont(juce::FontOptions(lit ? 13.0f : 12.0f,
                                   lit ? juce::Font::bold : juce::Font::plain));
        if (lit)
        {
            g.setColour(active[i].withAlpha(0.25f));
            g.drawText(labels[i], region.translated(0.7f, 1.1f),
                       juce::Justification::centredLeft, false);
        }
        g.setColour(lit ? active[i] : juce::Colour::fromRGB(187, 192, 185));
        g.drawText(labels[i], region, juce::Justification::centredLeft, false);
    }
}

'''
change('Source/PluginEditor.cpp',
       'TGZenerRackAudioProcessorEditor::TGZenerRackAudioProcessorEditor(TGZenerRackAudioProcessor& p)',
       button_code + 'TGZenerRackAudioProcessorEditor::TGZenerRackAudioProcessorEditor(TGZenerRackAudioProcessor& p)')
change('Source/PluginEditor.cpp',
       '    auto& apvts=processor.parameters;',
       '''    auto setupAttack = [this](TGAttackButton& button)
    {
        button.setSliderStyle(juce::Slider::LinearVertical);
        button.setRange(0.0, 2.0, 1.0);
        button.setTextBoxStyle(juce::Slider::NoTextBox, false, 0, 0);
        button.setTooltip("Attack: click to cycle Fast 1ms / Med 8ms / Slow 15ms");
        button.setLookAndFeel(&attackButtonLook);
        addAndMakeVisible(button);
    };
    setupAttack(attackL);
    setupAttack(attackR);

    auto& apvts=processor.parameters;''')
change('Source/PluginEditor.cpp',
       '    recLAttach=std::make_unique<SA>(apvts,"recovery",recoveryL);',
       '    recLAttach=std::make_unique<SA>(apvts,"recovery",recoveryL);\n'
       '    attLAttach=std::make_unique<SA>(apvts,"attack",attackL);')
change('Source/PluginEditor.cpp',
       '    recRAttach=std::make_unique<SA>(apvts,"recovery",recoveryR);',
       '    recRAttach=std::make_unique<SA>(apvts,"recovery",recoveryR);\n'
       '    attRAttach=std::make_unique<SA>(apvts,"attack",attackR);')
change('Source/PluginEditor.cpp',
       '    cellButton.setTooltip("Zener harmonic cell ON/OFF; limiter still works when OFF");',
       '    cellButton.setTooltip("THD harmonics ON/OFF; limiter still works when OFF");')
change('Source/PluginEditor.cpp',
       '    inLAttach.reset();outLAttach.reset();recLAttach.reset();',
       '    inLAttach.reset();outLAttach.reset();recLAttach.reset();attLAttach.reset();')
change('Source/PluginEditor.cpp',
       '    inRAttach.reset();outRAttach.reset();recRAttach.reset();',
       '    inRAttach.reset();outRAttach.reset();recRAttach.reset();attRAttach.reset();')
change('Source/PluginEditor.cpp',
       '        knob->setLookAndFeel(nullptr);\n}',
       '        knob->setLookAndFeel(nullptr);\n'
       '    attackL.setLookAndFeel(nullptr);\n'
       '    attackR.setLookAndFeel(nullptr);\n}')
change('Source/PluginEditor.cpp',
       '    recoveryL.setBounds(503,264,130,130);',
       '    recoveryL.setBounds(503,264,130,130);\n'
       '    attackL.setBounds(340,285,148,100);')
change('Source/PluginEditor.cpp',
       '    recoveryR.setBounds(1245,264,130,130);',
       '    recoveryR.setBounds(1245,264,130,130);\n'
       '    attackR.setBounds(1082,285,148,100);')

# Change only the obsolete ATTACK/LIMIT legends on the existing faceplate.
change('tools/generate_gui_assets.py',
       "    txt(d,'8ms  ATTACK',400+dx,256,9,PALE)\n    txt(d,'LIMIT',400+dx,272,12,GOLD,bold=True)",
       "    txt(d,'ATTACK',402+dx,255,11,GOLD,bold=True)")
change('tools/generate_gui_assets.py',
       "for cx, lab in ((723,'CELL'),(777,'IN')):",
       "for cx, lab in ((723,'THD'),(777,'IN')):")

# Add illuminated button previews matching the actual LookAndFeel dimensions.
preview_code = r'''

def draw_attack_button(d, ox, oy, mode):
    colors = [(240, 56, 41, 255), (255, 171, 62, 255), (87, 192, 255, 255)]
    c = colors[mode]
    # Same x/y origin, bezel size, label baseline and spacing as JUCE.
    bx = ox + 9; by = oy + 29
    rect(d, (bx+2,by+2,bx+44,by+44), fill=(3,5,7,255),r=4)
    rect(d, (bx,by,bx+42,by+42), fill=(18,21,25,255),outline=(155,166,171,255),width=1,r=4)
    rect(d, (bx+5,by+5,bx+37,by+37), fill=c, outline=(33,40,43,255), width=1, r=3)
    rect(d, (bx+8,by+7,bx+34,by+12),fill=tuple(min(255, int(t*.5+120)) for t in c[:3])+(255,),r=2)
    for i,(label,ms) in enumerate((('FAST','1ms'),('MED','8ms'),('SLOW','15ms'))):
        color=colors[i] if i==mode else (187,192,185,255)
        txt(d, label+' '+ms, ox+64, oy+22+i*28, 10, color, align='left', bold=i==mode)

'''
change('tools/generate_gui_assets.py',
       '# small toggle hardware for knee on faceplate',
       preview_code + '# small toggle hardware for knee on faceplate')
change('tools/generate_gui_assets.py',
       'preview.convert(\'RGB\').resize((W,H),Image.Resampling.LANCZOS).save(os.path.join(BASE,\'GUI_TG12413_Authentic_Preview.png\'),optimize=True)',
       '''# Three state previews use the same embedded faceplate and JUCE drawing coords.
for mode,name in enumerate(('Fast_Red','Med_Orange','Slow_Blue')):
    q=preview.copy()
    d0=ImageDraw.Draw(q)
    for dx in (0,742): draw_attack_button(d0,340+dx,285,mode)
    q.convert('RGB').resize((W,H),Image.Resampling.LANCZOS).save(
        os.path.join(BASE, 'GUI_Attack_'+name+'.png'),optimize=True)
# Default is MED 8ms.
q=preview.copy(); d0=ImageDraw.Draw(q)
for dx in (0,742): draw_attack_button(d0,340+dx,285,1)
q.convert('RGB').resize((W,H),Image.Resampling.LANCZOS).save(os.path.join(BASE,'GUI_TG12413_Authentic_Preview.png'),optimize=True)''')

# Give the new DSP behavior a native Windows regression test.
test_source = r'''#include "../Source/TGFastZenerLimiter.h"
#include <cmath>
#include <cstdio>
#include <stdexcept>
#include <array>
using namespace tgfast;
int main(int argc, char** argv)
{
    if (argc < 2) return 2;
    std::array<double,3> gr {};
    for (int mode=0; mode<3; ++mode)
    {
        TGFastZenerLimiter limiter;
        limiter.loadReference(argv[1]);
        limiter.prepare(44100.0);
        Controls c; c.inputPct=100; c.outputPct=50; c.attackMode=mode; c.recovery=1;
        limiter.setControls(c);
        limiter.setReferenceToneForValidation(1000.0);
        for (int i=0; i<int(44100*.006); ++i)
            limiter.process(amp(-18) * std::sin(2*PI*1000*i/44100.0));
        gr[mode]=limiter.currentGR();
        std::printf("Mode %d attack %.0fms 6ms GR %.4fdB\n", mode,attacks[mode],gr[mode]);
    }
    if (!(gr[0]>gr[1] && gr[1]>gr[2] && gr[2]>0.0))
        throw std::runtime_error("Attack modes do not show correctly ordered transient GR");
    return 0;
}
'''
(ROOT / 'tests/test_attack.cpp').write_text(test_source, encoding='utf-8')
change('CMakeLists.txt', 'VERSION 1.1.0', 'VERSION 1.2.0')
change('CMakeLists.txt',
       'foreach(test_name IN ITEMS basic controls program autotrack detector_clean spectra embedded_memory)',
       'foreach(test_name IN ITEMS basic controls program autotrack detector_clean spectra embedded_memory attack)')

print('Applied TG12413 v1.2 attack-mode DSP, click-cycle button, THD label, and GUI.')