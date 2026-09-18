import {useId, useState} from "react";

// Search is local; only choosing an exact option changes the server filter.
export function SearchableSelect({label, value, options, onChange}: {
  label: string; value: string; options: string[]; onChange: (value: string) => void;
}) {
  const id = useId();
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [active, setActive] = useState(-1);
  const choices = ["", ...options.filter(option => option.toLowerCase().includes(search.toLowerCase()))];
  function show() { setSearch(""); setActive(-1); setOpen(true); }
  function choose(option: string) { onChange(option); setOpen(false); setSearch(""); setActive(-1); }
  return <div className="searchable-select" onBlur={event => { if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false); }}>
    <label htmlFor={id}>{label}</label>
    <div className="searchable-select-input">
      <input id={id} role="combobox" aria-expanded={open} aria-controls={`${id}-options`} aria-autocomplete="list"
        aria-activedescendant={open && active >= 0 ? `${id}-${active}` : undefined}
        placeholder="All" value={open ? search : value} onFocus={show} onClick={() => { if (!open) show(); }}
        onChange={event => {setSearch(event.target.value); setActive(-1); setOpen(true);}}
        onKeyDown={event => {
          if (event.key === "Escape") {setOpen(false); event.preventDefault();}
          if (event.key === "ArrowDown" || event.key === "ArrowUp") {
            event.preventDefault(); setOpen(true);
            setActive(index => event.key === "ArrowDown" ? Math.min(index + 1, choices.length - 1) : Math.max(index - 1, 0));
          }
          if (event.key === "Enter" && open) {
            event.preventDefault();
            if (active >= 0) choose(choices[active]);
            else if (options.includes(search)) choose(search);
          }
        }} />
      <button type="button" aria-label={`Toggle ${label} options`} onClick={() => open ? setOpen(false) : show()}>▾</button>
    </div>
    {open ? <ul id={`${id}-options`} role="listbox" aria-label={`${label} options`}>
      {choices.map((option, index) => <li key={option} id={`${id}-${index}`} role="option" aria-selected={option === value}
        className={active === index ? "highlighted" : ""} onMouseDown={event => event.preventDefault()} onClick={() => choose(option)}>{option || "All"}</li>)}
      {choices.length === 1 && search ? <li className="muted">No matches</li> : null}
    </ul> : null}
  </div>;
}
