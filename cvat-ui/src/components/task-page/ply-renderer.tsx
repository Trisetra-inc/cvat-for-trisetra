// Copyright (C) 2019-2022 Intel Corporation
//
// SPDX-License-Identifier: MIT

import React from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';
import { PLYLoader } from 'three/examples/jsm/loaders/PLYLoader';

interface PLYRendererProps {
    plyFile: string;
    lastModified: string;
}

export function PLYRenderer(props: PLYRendererProps): JSX.Element {
    const { plyFile, lastModified } = props;
    React.useEffect(() => {
        const canvas = document.getElementById('my_canvas') as HTMLCanvasElement;

        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(45, canvas.width / canvas.height, 0.1, 100);
        camera.position.setScalar(5);
        const renderer = new THREE.WebGLRenderer({
            canvas,
            antialias: true,
        });

        const controls = new OrbitControls(camera, canvas);
        console.log(controls);
        const light = new THREE.DirectionalLight(0xffffff, 0.5);
        light.position.setScalar(10);
        scene.add(light);
        scene.add(new THREE.AmbientLight(0xffffff, 0.5));

        const loader = new PLYLoader();
        loader.load(plyFile, (geometry) => {
            const material = new THREE.MeshStandardMaterial({
                // color: 0x0055ff,
                flatShading: true,
            });
            const mesh = new THREE.Mesh(geometry, material);

            mesh.position.y = -0.2;
            mesh.position.z = 0.3;
            mesh.rotation.x = -Math.PI / 2;
            mesh.scale.multiplyScalar(0.01);

            scene.add(mesh);
        });

        function resize(render: THREE.WebGLRenderer): boolean {
            const width = canvas.clientWidth;
            const height = canvas.clientHeight;
            const needResize = canvas.width !== width || canvas.height !== height;
            if (needResize) {
                render.setSize(width, height, false);
            }
            return needResize;
        }

        renderer.setAnimationLoop(() => {
            if (resize(renderer)) {
                camera.aspect = canvas.clientWidth / canvas.clientHeight;
                camera.updateProjectionMatrix();
            }
            renderer.render(scene, camera);
        });
    }, []);
    return (
        <div
            style={{
                height: '350px',
                width: 'auto',
                maxWidth: '100%',
                maxHeight: '100%',
                minWidth: '40%',
                marginTop: '5%',
                margin: '2%',
                alignItems: 'center',
                textAlign: 'center',
            }}
            className='plyLoader'
        >
            <p>{`PLY Last Modified: ${lastModified}`}</p>
            <canvas style={{ width: '100%', height: '100%' }} id='my_canvas' />
        </div>
    );
}
