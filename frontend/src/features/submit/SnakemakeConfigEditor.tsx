import {ChevronDown, ChevronRight, RotateCcw, ShieldCheck} from "lucide-react";
import {useCallback, useEffect, useRef, useState} from "react";

import type {
  NiptRunMode,
  PgtaTarget,
  PipelineConfigTemplate,
  RuntimeProfileSummary,
} from "../../api";
import {getPipelineConfigTemplate, validatePipelineConfig} from "../../api";
import {errorMessage} from "../../lib/errors";


export type SnakemakeConfigSelection = {
  runtimeProfileId: string;
  configTemplateHash: string;
  configYaml: string;
  profile: RuntimeProfileSummary;
  changedPaths: string[];
  valid: boolean;
  dirty: boolean;
};

export function SnakemakeConfigEditor({
  pipeline,
  target,
  runMode,
  cores,
  onChange,
}: {
  pipeline: "pgta" | "nipt_docker";
  target: PgtaTarget;
  runMode: NiptRunMode;
  cores: number;
  onChange: (selection: SnakemakeConfigSelection | null) => void;
}) {
  const [template, setTemplate] = useState<PipelineConfigTemplate | null>(null);
  const [yaml, setYaml] = useState("");
  const [defaultYaml, setDefaultYaml] = useState("");
  const [changedPaths, setChangedPaths] = useState<string[]>([]);
  const [valid, setValid] = useState(false);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [validating, setValidating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestSequence = useRef(0);

  const publish = useCallback((
    nextTemplate: PipelineConfigTemplate,
    nextYaml: string,
    nextValid: boolean,
    nextChangedPaths: string[],
    nextDefaultYaml: string,
  ) => {
    onChange({
      runtimeProfileId: nextTemplate.profile.id,
      configTemplateHash: nextTemplate.config_template_hash,
      configYaml: nextYaml,
      profile: nextTemplate.profile,
      changedPaths: nextChangedPaths,
      valid: nextValid,
      dirty: nextYaml !== nextDefaultYaml,
    });
  }, [onChange]);

  const loadTemplate = useCallback(async (profileId?: string) => {
    const requestId = ++requestSequence.current;
    setLoading(true);
    setValidating(false);
    setError(null);
    onChange(null);
    try {
      const next = await getPipelineConfigTemplate({pipeline, target, runMode, profileId});
      if (requestId !== requestSequence.current) return;
      const validation = await validatePipelineConfig({
        pipeline,
        target,
        run_mode: runMode,
        cores: pipeline === "nipt_docker" ? cores : undefined,
        runtime_profile_id: next.profile.id,
        config_template_hash: next.config_template_hash,
        snakemake_config_yaml: next.editable_yaml,
      });
      if (requestId !== requestSequence.current) return;
      const validatedTemplate = {...next, profile: validation.profile, config_template_hash: validation.config_template_hash};
      setTemplate(validatedTemplate);
      setYaml(validation.normalized_yaml);
      setDefaultYaml(next.editable_yaml);
      setChangedPaths(validation.changed_paths);
      setValid(true);
      publish(validatedTemplate, validation.normalized_yaml, true, validation.changed_paths, next.editable_yaml);
    } catch (loadError) {
      if (requestId !== requestSequence.current) return;
      setTemplate(null);
      setYaml("");
      setDefaultYaml("");
      setChangedPaths([]);
      setValid(false);
      setError(errorMessage(loadError));
    } finally {
      if (requestId === requestSequence.current) setLoading(false);
    }
  }, [cores, onChange, pipeline, publish, runMode, target]);

  useEffect(() => {
    void loadTemplate();
  }, [loadTemplate]);

  function handleProfileChange(profileId: string) {
    if (yaml !== defaultYaml && !window.confirm("Discard the edited Snakemake config and load this runtime profile?")) return;
    void loadTemplate(profileId);
  }

  function handleYamlChange(nextYaml: string) {
    requestSequence.current += 1;
    setYaml(nextYaml);
    setValid(false);
    setValidating(false);
    setChangedPaths([]);
    setError(null);
    if (template) publish(template, nextYaml, false, [], defaultYaml);
  }

  function resetDefaults() {
    if (!template) return;
    requestSequence.current += 1;
    setYaml(defaultYaml);
    setChangedPaths([]);
    setValid(true);
    setError(null);
    publish(template, defaultYaml, true, [], defaultYaml);
  }

  async function validate() {
    if (!template) return;
    const requestId = ++requestSequence.current;
    setValidating(true);
    setError(null);
    try {
      const result = await validatePipelineConfig({
        pipeline,
        target,
        run_mode: runMode,
        cores: pipeline === "nipt_docker" ? cores : undefined,
        runtime_profile_id: template.profile.id,
        config_template_hash: template.config_template_hash,
        snakemake_config_yaml: yaml,
      });
      if (requestId !== requestSequence.current) return;
      const nextTemplate = {...template, profile: result.profile, config_template_hash: result.config_template_hash};
      setTemplate(nextTemplate);
      setYaml(result.normalized_yaml);
      setChangedPaths(result.changed_paths);
      setValid(true);
      publish(nextTemplate, result.normalized_yaml, true, result.changed_paths, defaultYaml);
    } catch (validationError) {
      if (requestId !== requestSequence.current) return;
      setValid(false);
      setChangedPaths([]);
      setError(errorMessage(validationError));
      publish(template, yaml, false, [], defaultYaml);
    } finally {
      if (requestId === requestSequence.current) setValidating(false);
    }
  }

  return (
    <div className="snakemake-config-shell">
      <label className="field">
        <span>Runtime profile</span>
        <select
          aria-label="Runtime profile"
          disabled={loading || validating || !template}
          value={template?.profile.id || ""}
          onChange={(event) => handleProfileChange(event.target.value)}
        >
          {(template?.profiles || []).map((profile) => (
            <option key={profile.id} value={profile.id}>{profile.label}</option>
          ))}
        </select>
        <small>{template ? `${template.profile.pipeline_version} / config ${template.profile.config_version}` : "Loading approved profiles"}</small>
      </label>

      <button
        aria-expanded={open}
        className="advanced-config-toggle"
        type="button"
        onClick={() => setOpen((current) => !current)}
      >
        {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        <span>Advanced Snakemake config</span>
        <small>{loading ? "Loading" : valid ? `${changedPaths.length} modified` : "Validation required"}</small>
      </button>

      {open ? (
        <div className="snakemake-config-editor">
          <div className="config-editor-heading">
            <div>
              <strong>Editable YAML</strong>
              <span>Only approved Snakemake fields are accepted. Runtime and Docker settings remain locked.</span>
            </div>
            <div className="panel-actions compact">
              <button className="button ghost" type="button" disabled={!template || validating} onClick={resetDefaults}>
                <RotateCcw size={14} /> Reset defaults
              </button>
              <button className="button primary" type="button" disabled={!template || validating || loading} onClick={() => void validate()}>
                <ShieldCheck size={14} /> {validating ? "Validating" : "Validate"}
              </button>
            </div>
          </div>
          <label className="field full">
            <span>Snakemake config YAML</span>
            <textarea
              aria-label="Snakemake config YAML"
              className="config-yaml-editor"
              disabled={!template || loading}
              rows={14}
              spellCheck={false}
              value={yaml}
              onChange={(event) => handleYamlChange(event.target.value)}
            />
          </label>
          <div className={valid ? "config-validation-state valid" : "config-validation-state pending"}>
            <ShieldCheck size={15} />
            <span>{valid ? `${changedPaths.length} modified field${changedPaths.length === 1 ? "" : "s"}; config validated` : "Validate this edit before creating the run"}</span>
          </div>
          {changedPaths.length ? <p className="config-changed-paths">{changedPaths.join(" · ")}</p> : null}
          {error ? <p className="inline-error" role="alert">{error}</p> : null}
        </div>
      ) : null}
    </div>
  );
}
